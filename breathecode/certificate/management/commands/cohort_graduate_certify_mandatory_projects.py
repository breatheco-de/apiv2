"""
For a single cohort or every micro of a macro cohort: align STUDENT educational_status
with legacy mandatory PROJECT completion (revision_status APPROVED or IGNORED).

- Promote to GRADUATED when all mandatory projects are complete.
- Demote GRADUATED → ACTIVE when mandatory projects are still pending.
- Optionally call generate_certificate for every GRADUATED STUDENT on that cohort.

This command intentionally ignores grading_strategy.completion and only checks mandatory
PROJECT slugs from the syllabus JSON (classic legacy graduation rule).
"""

from __future__ import annotations

from capyc.rest_framework.exceptions import ValidationException
from django.core.management.base import BaseCommand, CommandError

from django.contrib.auth.models import User

from breathecode.admissions.models import ACTIVE, GRADUATED, LATE, STUDENT, Cohort, CohortUser
from breathecode.certificate.actions import (
    generate_certificate,
    get_assets_from_syllabus,
    how_many_pending_tasks,
)
from breathecode.certificate.management.commands.macro_cohort_certificates import ordered_micro_cohorts


def _mandatory_projects_completion(user: User, cohort: Cohort) -> tuple[bool, dict]:
    if not cohort.syllabus_version:
        return (False, {"reason": "cohort has no syllabus_version"})

    project_slugs = get_assets_from_syllabus(
        cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True
    )
    if not project_slugs:
        return (
            False,
            {
                "reason": "syllabus has no mandatory PROJECT slugs",
                "projects_total": 0,
                "projects_pending": 0,
            },
        )

    pending = how_many_pending_tasks(
        cohort.syllabus_version,
        user,
        task_types=["PROJECT"],
        only_mandatory=True,
        cohort_id=cohort.id,
    )
    completed = len(project_slugs) - pending
    pct = round((completed / len(project_slugs)) * 100, 2)
    ok = pending == 0

    return (
        ok,
        {
            "projects_total": len(project_slugs),
            "projects_completed": completed,
            "projects_pending": pending,
            "projects_done_pct": pct,
        },
    )


class Command(BaseCommand):
    help = (
        "Align STUDENT educational_status with mandatory PROJECT completion (classic legacy rule). "
        "Graduates when all mandatory projects are APPROVED/IGNORED; demotes GRADUATED → ACTIVE "
        "when they are not. Optionally issues certificates. "
        "Target one cohort (--cohort-id/--cohort-slug) or every micro of a macro "
        "(--macro-cohort-id/--macro-cohort-slug)."
    )

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--cohort-id", type=int, help="Cohort primary key (single cohort)")
        g.add_argument("--cohort-slug", type=str, help="Cohort slug (single cohort)")
        g.add_argument("--macro-cohort-id", type=int, help="Macro cohort primary key (all linked micro cohorts)")
        g.add_argument("--macro-cohort-slug", type=str, help="Macro cohort slug (all linked micro cohorts)")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "No escribe en BD. Lista quién pasaría a GRADUATED, quién volvería a ACTIVE "
                "y a quién se le intentaría generar certificado."
            ),
        )
        parser.add_argument(
            "--layout-slug",
            type=str,
            default=None,
            help="Layout slug passed to generate_certificate.",
        )
        parser.add_argument(
            "--skip-certificates",
            action="store_true",
            help="Only perform graduation/demotion; do not call generate_certificate.",
        )

    def handle(self, *args, **options):
        macro_id = options.get("macro_cohort_id")
        macro_slug = options.get("macro_cohort_slug")

        if macro_id is not None or macro_slug is not None:
            macro = self._resolve_macro(macro_id, macro_slug)
            micros = ordered_micro_cohorts(macro)
            if not micros:
                raise CommandError(
                    f"Macro cohort '{macro.slug}' has no linked micro cohorts "
                    "(or all are DELETED). Link micro cohorts via Cohort.micro_cohorts."
                )

            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 72}"))
            self.stdout.write(self.style.SUCCESS(f"Macro cohort: {macro.name} (id={macro.id}, slug={macro.slug})"))
            self.stdout.write(
                self.style.SUCCESS(f"Micro cohorts ({len(micros)}): {', '.join(f'{m.slug}#{m.id}' for m in micros)}")
            )
            self.stdout.write(self.style.SUCCESS(f"{'=' * 72}\n"))

            grand_totals = self._empty_totals()
            for micro in micros:
                self.stdout.write(self.style.MIGRATE_HEADING(f"\n▶ Micro cohort: {micro.name} (id={micro.id})"))
                try:
                    summary = self._process_cohort(micro, options)
                except CommandError as e:
                    self.stdout.write(self.style.ERROR(f"  SKIP micro {micro.slug!r}: {e}"))
                    grand_totals["micros_skipped"] += 1
                    continue
                self._accumulate_totals(grand_totals, summary)
                grand_totals["micros_processed"] += 1

            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 72}"))
            self.stdout.write(self.style.SUCCESS("Macro summary"))
            self._print_totals(grand_totals, skip_certificates=options["skip_certificates"])
            self.stdout.write(self.style.SUCCESS(f"{'=' * 72}\n"))
            return

        cohort = self._resolve_single_cohort(options)
        self._process_cohort(cohort, options)

    def _resolve_macro(self, macro_id: int | None, macro_slug: str | None) -> Cohort:
        if macro_id is not None:
            macro = Cohort.objects.filter(id=macro_id).first()
            if macro is None:
                raise CommandError(f"No cohort found with id={macro_id}")
            return macro

        slug = macro_slug.strip()
        macro = Cohort.objects.filter(slug=slug).first()
        if macro is None:
            raise CommandError(f"No cohort found with slug={slug!r}")
        return macro

    def _resolve_single_cohort(self, options) -> Cohort:
        if options.get("cohort_id") is not None:
            cohort = Cohort.objects.filter(id=options["cohort_id"]).first()
            if not cohort:
                raise CommandError(f"No cohort with id={options['cohort_id']}")
            return cohort

        slug = options["cohort_slug"].strip()
        cohort = Cohort.objects.filter(slug=slug).first()
        if not cohort:
            raise CommandError(f"No cohort with slug={slug!r}")
        return cohort

    @staticmethod
    def _empty_totals() -> dict:
        return {
            "micros_processed": 0,
            "micros_skipped": 0,
            "graduated_new": 0,
            "demoted_to_active": 0,
            "already_graduated_complete": 0,
            "skipped_incomplete": 0,
            "skipped_no_assets": 0,
            "skipped_late": 0,
            "cert_ok": 0,
            "cert_fail": 0,
        }

    @staticmethod
    def _accumulate_totals(grand: dict, summary: dict) -> None:
        for key in (
            "graduated_new",
            "demoted_to_active",
            "already_graduated_complete",
            "skipped_incomplete",
            "skipped_no_assets",
            "skipped_late",
            "cert_ok",
            "cert_fail",
        ):
            grand[key] += summary.get(key, 0)

    def _process_cohort(self, cohort: Cohort, options) -> dict:
        dry_run = options["dry_run"]
        layout_slug = options["layout_slug"]
        skip_certificates = options["skip_certificates"]

        if cohort.stage == "DELETED":
            raise CommandError(f"Cohort {cohort.slug!r} is DELETED.")
        if not cohort.syllabus_version:
            raise CommandError(f"Cohort {cohort.slug!r} has no syllabus_version.")

        self.stdout.write(self.style.NOTICE(f"Cohort: {cohort.name} (id={cohort.id}, slug={cohort.slug})"))
        self.stdout.write(
            self.style.NOTICE(
                f"  Mode: {'DRY RUN (no writes)' if dry_run else 'WRITE'}; "
                f"rule=mandatory PROJECT (APPROVED/IGNORED); skip_certificates={skip_certificates}"
            )
        )

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"DRY RUN — Graduación / democión (cohort id={cohort.id} slug={cohort.slug!r})"
                )
            )

        students = (
            CohortUser.objects.filter(cohort=cohort, role=STUDENT)
            .exclude(cohort__stage="DELETED")
            .select_related("user")
            .order_by("id")
        )

        skipped_incomplete = 0
        skipped_late = 0
        skipped_no_assets = 0
        graduated_new = 0
        demoted_to_active = 0
        already_graduated_complete = 0
        dry_run_would_graduate: list[CohortUser] = []

        for cu in students:
            ok, meta = _mandatory_projects_completion(cu.user, cohort)
            if meta.get("reason") == "syllabus has no mandatory PROJECT slugs":
                skipped_no_assets += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP user_id={cu.user_id} ({cu.user.email}): no mandatory PROJECT slugs in syllabus."
                    )
                )
                continue

            if cu.educational_status == GRADUATED and not ok:
                if dry_run:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [dry-run] DEMOTE → ACTIVE — cohort_user id={cu.id} user_id={cu.user_id} "
                            f"email={cu.user.email!r} pending_mandatory_projects={meta.get('projects_pending')} "
                            f"({meta.get('projects_done_pct')}% done)"
                        )
                    )
                else:
                    cu.educational_status = ACTIVE
                    cu.save(update_fields=["educational_status", "updated_at"])
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ACTIVE (demoted) cohort_user id={cu.id} user={cu.user.email!r} — "
                            f"pending mandatory projects={meta.get('projects_pending')}"
                        )
                    )
                demoted_to_active += 1
                continue

            if not ok:
                skipped_incomplete += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP user_id={cu.user_id} ({cu.user.email}): "
                        f"projects {meta.get('projects_done_pct')}% "
                        f"({meta.get('projects_pending')} pending of {meta.get('projects_total')})"
                    )
                )
                continue

            if cu.finantial_status == LATE:
                skipped_late += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  SKIP graduation user_id={cu.user_id} ({cu.user.email}): finantial_status=LATE"
                    )
                )
                continue

            if cu.educational_status == GRADUATED:
                already_graduated_complete += 1
                if dry_run:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"  [dry-run] ya GRADUATED (sin cambio) — cohort_user id={cu.id} "
                            f"user_id={cu.user_id} email={cu.user.email!r}"
                        )
                    )
                continue

            if dry_run:
                dry_run_would_graduate.append(cu)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [dry-run] GRADUARÍA — cohort_user id={cu.id} user_id={cu.user_id} "
                        f"email={cu.user.email!r} (educational_status actual={cu.educational_status!r})"
                    )
                )
                graduated_new += 1
            else:
                cu.educational_status = GRADUATED
                cu.save(update_fields=["educational_status", "updated_at"])
                self.stdout.write(
                    self.style.SUCCESS(f"  GRADUATED cohort_user id={cu.id} user={cu.user.email!r}")
                )
                graduated_new += 1

        cert_ok = 0
        cert_fail = 0

        if not skip_certificates:
            if dry_run:
                self.stdout.write("")
                self.stdout.write(
                    self.style.MIGRATE_HEADING(
                        f"DRY RUN — Certificados (cohort id={cohort.id} slug={cohort.slug!r})"
                    )
                )
                graduated_in_db = list(
                    CohortUser.objects.filter(cohort=cohort, role=STUDENT, educational_status=GRADUATED)
                    .exclude(cohort__stage="DELETED")
                    .select_related("user")
                    .order_by("id")
                )
                by_cu_id: dict[int, tuple[CohortUser, str]] = {}
                for cu in graduated_in_db:
                    by_cu_id[cu.id] = (cu, "ya GRADUATED en BD")
                for cu in dry_run_would_graduate:
                    by_cu_id[cu.id] = (cu, "pasaría a GRADUATED en este run")
                for _cu_id, (cu, reason) in sorted(by_cu_id.items(), key=lambda x: x[0]):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [dry-run] CERT → generate_certificate — {reason} — cohort_user id={cu.id} "
                            f"user_id={cu.user_id} email={cu.user.email!r}"
                        )
                    )
                    cert_ok += 1
            else:
                for cu in (
                    CohortUser.objects.filter(cohort=cohort, role=STUDENT, educational_status=GRADUATED)
                    .exclude(cohort__stage="DELETED")
                    .select_related("user")
                    .order_by("id")
                ):
                    try:
                        generate_certificate(cu.user, cohort, layout_slug)
                        self.stdout.write(
                            self.style.SUCCESS(f"  CERT OK user={cu.user.email!r} cohort_user_id={cu.id}")
                        )
                        cert_ok += 1
                    except ValidationException as e:
                        self.stdout.write(
                            self.style.ERROR(f"  CERT FAIL user={cu.user.email!r}: {e}")
                        )
                        cert_fail += 1

        summary = {
            "graduated_new": graduated_new,
            "demoted_to_active": demoted_to_active,
            "already_graduated_complete": already_graduated_complete,
            "skipped_incomplete": skipped_incomplete,
            "skipped_no_assets": skipped_no_assets,
            "skipped_late": skipped_late,
            "cert_ok": cert_ok,
            "cert_fail": cert_fail,
        }

        self.stdout.write(self.style.NOTICE("\nSummary"))
        self._print_totals(summary, skip_certificates=skip_certificates, cohort=cohort, dry_run=dry_run)

        return summary

    def _print_totals(
        self,
        totals: dict,
        *,
        skip_certificates: bool,
        cohort: Cohort | None = None,
        dry_run: bool = False,
    ) -> None:
        self.stdout.write(
            self.style.NOTICE(
                f"  graduated_new={totals['graduated_new']}, "
                f"demoted_to_active={totals['demoted_to_active']}, "
                f"already_GRADUATED_and_complete={totals['already_graduated_complete']}, "
                f"skipped_incomplete={totals['skipped_incomplete']}, "
                f"skipped_no_mandatory_project_slugs={totals['skipped_no_assets']}, "
                f"skipped_late_financial={totals['skipped_late']}"
            )
        )
        if "micros_processed" in totals:
            self.stdout.write(
                self.style.NOTICE(
                    f"  micros_processed={totals['micros_processed']}, micros_skipped={totals['micros_skipped']}"
                )
            )
        if not skip_certificates:
            self.stdout.write(
                self.style.NOTICE(f"  certificate_ok={totals['cert_ok']}, certificate_failed={totals['cert_fail']}")
            )
        if dry_run and cohort is not None:
            db_grad_total = (
                CohortUser.objects.filter(cohort=cohort, role=STUDENT, educational_status=GRADUATED)
                .exclude(cohort__stage="DELETED")
                .count()
            )
            self.stdout.write(
                self.style.NOTICE(
                    f"  [dry-run] Resumen cohort {cohort.slug!r}: "
                    f"graduaría a {totals['graduated_new']}, "
                    f"demovería a ACTIVE {totals['demoted_to_active']}; "
                    f"{totals['already_graduated_complete']} ya GRADUATED con proyectos obligatorios al 100%."
                )
            )
            if not skip_certificates:
                cert_planned_union = db_grad_total + totals["graduated_new"] - totals["demoted_to_active"]
                self.stdout.write(
                    self.style.NOTICE(
                        f"  [dry-run] Tras ejecutar escritura: ~{max(cert_planned_union, 0)} intento(s) de certificado."
                    )
                )
