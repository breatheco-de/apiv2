"""
For a single cohort or every micro of a macro cohort: mark STUDENT cohort users as GRADUATED
when LESSON + EXERCISE syllabus completion is 100% (by Task.task_status=DONE), then run
generate_certificate for every GRADUATED STUDENT on that cohort.

Does not require PROJECT entries in the syllabus. Certificate issuance still follows
generate_certificate (financial status, cohort ended / never_ends, etc.).
"""

from __future__ import annotations

from capyc.rest_framework.exceptions import ValidationException
from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import CERTIFICATE_RECIPIENT_ROLES, GRADUATED, LATE, STUDENT, Cohort, CohortUser
from breathecode.assignments.models import Task
from breathecode.certificate.actions import (
    generate_certificate,
    generate_certificate_ignoring_tasks,
    get_assets_from_syllabus,
)
from breathecode.certificate.management.commands.macro_cohort_certificates import ordered_micro_cohorts


def _completion_rate(user_id: int, cohort_id: int, task_type: str, slugs: list[str]) -> float:
    if not slugs:
        return 100.0
    done = (
        Task.objects.filter(
            user_id=user_id,
            cohort_id=cohort_id,
            task_type=task_type,
            associated_slug__in=slugs,
            task_status=Task.TaskStatus.DONE,
        )
        .values("associated_slug")
        .distinct()
        .count()
    )
    return (done / len(slugs)) * 100.0


def _lesson_exercise_completion(user_id: int, cohort: Cohort, *, only_mandatory: bool) -> tuple[bool, dict]:
    if not cohort.syllabus_version:
        return (False, {"reason": "cohort has no syllabus_version"})

    lesson_slugs = get_assets_from_syllabus(
        cohort.syllabus_version, task_types=["LESSON"], only_mandatory=only_mandatory
    )
    exercise_slugs = get_assets_from_syllabus(
        cohort.syllabus_version, task_types=["EXERCISE"], only_mandatory=only_mandatory
    )

    if not lesson_slugs and not exercise_slugs:
        return (
            False,
            {
                "reason": "syllabus has no LESSON or EXERCISE slugs for this cohort version",
                "lessons_total": 0,
                "exercises_total": 0,
            },
        )

    lesson_rate = _completion_rate(user_id, cohort.id, "LESSON", lesson_slugs)
    exercise_rate = _completion_rate(user_id, cohort.id, "EXERCISE", exercise_slugs)

    ok = lesson_rate >= 100.0 and exercise_rate >= 100.0
    meta = {
        "lessons_total": len(lesson_slugs),
        "exercises_total": len(exercise_slugs),
        "lessons_done_pct": round(lesson_rate, 2),
        "exercises_done_pct": round(exercise_rate, 2),
    }
    return (ok, meta)


class Command(BaseCommand):
    help = (
        "Mark STUDENTs as GRADUATED when they have 100% LESSON and 100% EXERCISE completion, "
        "then call generate_certificate for all GRADUATED STUDENTs. "
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
                "No escribe en BD. Lista por cohort quién pasaría a GRADUATED y a quién se le intentaría "
                "generar certificado (incluye graduaciones simuladas que aún no están en la BD)."
            ),
        )
        parser.add_argument(
            "--layout-slug",
            type=str,
            default=None,
            help="Layout slug passed to generate_certificate.",
        )
        parser.add_argument(
            "--only-mandatory",
            action="store_true",
            help="Count only mandatory LESSON/EXERCISE slugs from the syllabus JSON.",
        )
        parser.add_argument(
            "--skip-certificates",
            action="store_true",
            help="Only perform the graduation step; do not call generate_certificate.",
        )
        parser.add_argument(
            "--ignore-pending-projects",
            action="store_true",
            help=(
                "Call generate_certificate_ignoring_tasks instead of generate_certificate "
                "(useful when the syllabus has PROJECT slugs still pending)."
            ),
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
            self._print_totals(grand_totals, options, skip_certificates=options["skip_certificates"])
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
        only_mandatory = options["only_mandatory"]
        layout_slug = options["layout_slug"]
        skip_certificates = options["skip_certificates"]
        ignore_pending_projects = options["ignore_pending_projects"]

        if cohort.stage == "DELETED":
            raise CommandError(f"Cohort {cohort.slug!r} is DELETED.")
        if not cohort.syllabus_version:
            raise CommandError(f"Cohort {cohort.slug!r} has no syllabus_version.")

        self.stdout.write(self.style.NOTICE(f"Cohort: {cohort.name} (id={cohort.id}, slug={cohort.slug})"))
        certify_fn = generate_certificate_ignoring_tasks if ignore_pending_projects else generate_certificate
        self.stdout.write(
            self.style.NOTICE(
                f"  Mode: {'DRY RUN (no writes)' if dry_run else 'WRITE'}; "
                f"only_mandatory={only_mandatory}; skip_certificates={skip_certificates}; "
                f"certificate={'ignoring_projects' if ignore_pending_projects else 'strict'}"
            )
        )

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"DRY RUN — Graduaciones (cohort id={cohort.id} slug={cohort.slug!r})"
                )
            )

        students = (
            CohortUser.objects.filter(cohort=cohort, role__in=CERTIFICATE_RECIPIENT_ROLES)
            .exclude(cohort__stage="DELETED")
            .select_related("user")
            .order_by("id")
        )

        skipped_incomplete = 0
        skipped_late = 0
        skipped_no_assets = 0
        graduated_new = 0
        already_graduated_complete = 0
        dry_run_would_graduate: list[CohortUser] = []

        for cu in students:
            ok, meta = _lesson_exercise_completion(cu.user_id, cohort, only_mandatory=only_mandatory)
            if meta.get("reason") == "syllabus has no LESSON or EXERCISE slugs for this cohort version":
                skipped_no_assets += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP user_id={cu.user_id} ({cu.user.email}): no LESSON/EXERCISE in syllabus scope."
                    )
                )
                continue
            if not ok:
                skipped_incomplete += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP user_id={cu.user_id} ({cu.user.email}): "
                        f"lessons {meta.get('lessons_done_pct')}% / exercises {meta.get('exercises_done_pct')}%"
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
                cert_fn_label = (
                    "generate_certificate_ignoring_tasks"
                    if ignore_pending_projects
                    else "generate_certificate"
                )
                graduated_in_db = list(
                    CohortUser.objects.filter(
                        cohort=cohort, role__in=CERTIFICATE_RECIPIENT_ROLES, educational_status=GRADUATED
                    )
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
                            f"  [dry-run] CERT → {cert_fn_label} — {reason} — cohort_user id={cu.id} "
                            f"user_id={cu.user_id} email={cu.user.email!r}"
                        )
                    )
                    cert_ok += 1
            else:
                for cu in (
                    CohortUser.objects.filter(
                        cohort=cohort, role__in=CERTIFICATE_RECIPIENT_ROLES, educational_status=GRADUATED
                    )
                    .exclude(cohort__stage="DELETED")
                    .select_related("user")
                    .order_by("id")
                ):
                    try:
                        certify_fn(cu.user, cohort, layout_slug)
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
            "already_graduated_complete": already_graduated_complete,
            "skipped_incomplete": skipped_incomplete,
            "skipped_no_assets": skipped_no_assets,
            "skipped_late": skipped_late,
            "cert_ok": cert_ok,
            "cert_fail": cert_fail,
        }

        self.stdout.write(self.style.NOTICE("\nSummary"))
        self._print_totals(summary, options, skip_certificates=skip_certificates, cohort=cohort, dry_run=dry_run)

        return summary

    def _print_totals(
        self,
        totals: dict,
        options,
        *,
        skip_certificates: bool,
        cohort: Cohort | None = None,
        dry_run: bool = False,
    ) -> None:
        self.stdout.write(
            self.style.NOTICE(
                f"  graduated_new={totals['graduated_new']}, "
                f"already_GRADUATED_and_complete={totals['already_graduated_complete']}, "
                f"skipped_incomplete={totals['skipped_incomplete']}, "
                f"skipped_no_lesson_or_exercise_slugs={totals['skipped_no_assets']}, "
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
                CohortUser.objects.filter(
                    cohort=cohort, role__in=CERTIFICATE_RECIPIENT_ROLES, educational_status=GRADUATED
                )
                .exclude(cohort__stage="DELETED")
                .count()
            )
            self.stdout.write(
                self.style.NOTICE(
                    f"  [dry-run] Resumen cohort {cohort.slug!r}: "
                    f"graduaría a {totals['graduated_new']} STUDENT(s); "
                    f"{totals['already_graduated_complete']} ya GRADUATED con lecciones+ejs al 100%."
                )
            )
            if not skip_certificates:
                cert_planned_union = db_grad_total + totals["graduated_new"]
                self.stdout.write(
                    self.style.NOTICE(
                        f"  [dry-run] Tras ejecutar escritura: ~{cert_planned_union} intento(s) de certificado "
                        f"(GRADUATED en BD hoy={db_grad_total} + nuevos graduados={totals['graduated_new']})."
                    )
                )
