"""
For a single cohort: mark STUDENT cohort users as GRADUATED when LESSON + EXERCISE syllabus
completion is 100% (by Task.task_status=DONE), then run generate_certificate for every GRADUATED
STUDENT on that cohort.

Does not require PROJECT entries in the syllabus. Certificate issuance still follows
generate_certificate (financial status, cohort ended / never_ends, etc.).
"""

from __future__ import annotations

from capyc.rest_framework.exceptions import ValidationException
from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import GRADUATED, LATE, STUDENT, Cohort, CohortUser
from breathecode.assignments.models import Task
from breathecode.certificate.actions import (
    generate_certificate,
    generate_certificate_ignoring_tasks,
    get_assets_from_syllabus,
)


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
        "Mark STUDENTs as GRADUATED when they have 100% LESSON and 100% EXERCISE completion for the cohort "
        "syllabus, then call generate_certificate for all GRADUATED STUDENTs on that cohort."
    )

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--cohort-id", type=int, help="Cohort primary key")
        g.add_argument("--cohort-slug", type=str, help="Cohort slug")
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
        dry_run = options["dry_run"]
        only_mandatory = options["only_mandatory"]
        layout_slug = options["layout_slug"]
        skip_certificates = options["skip_certificates"]
        ignore_pending_projects = options["ignore_pending_projects"]

        if options.get("cohort_id") is not None:
            cohort = Cohort.objects.filter(id=options["cohort_id"]).first()
            if not cohort:
                raise CommandError(f"No cohort with id={options['cohort_id']}")
        else:
            slug = options["cohort_slug"].strip()
            cohort = Cohort.objects.filter(slug=slug).first()
            if not cohort:
                raise CommandError(f"No cohort with slug={slug!r}")

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
            CohortUser.objects.filter(cohort=cohort, role=STUDENT)
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
        dry_run_already_graduated_eligible: list[CohortUser] = []

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
                    dry_run_already_graduated_eligible.append(cu)
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
                self.stdout.write(
                    self.style.NOTICE(
                        "  Igual que en modo escritura después del paso 1: cada STUDENT con GRADUATED en BD "
                        "más quien este comando graduaría ahora (simulación; mismas validaciones al generar)."
                    )
                )
                cert_fn_label = (
                    "generate_certificate_ignoring_tasks"
                    if ignore_pending_projects
                    else "generate_certificate"
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
                            f"  [dry-run] CERT → {cert_fn_label} — {reason} — cohort_user id={cu.id} "
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

        self.stdout.write(self.style.NOTICE("\nSummary"))
        self.stdout.write(
            self.style.NOTICE(
                f"  graduated_new={graduated_new}, already_GRADUATED_and_complete={already_graduated_complete}, "
                f"skipped_incomplete={skipped_incomplete}, skipped_no_lesson_or_exercise_slugs={skipped_no_assets}, "
                f"skipped_late_financial={skipped_late}"
            )
        )
        if not skip_certificates:
            self.stdout.write(self.style.NOTICE(f"  certificate_ok={cert_ok}, certificate_failed={cert_fail}"))
        if dry_run:
            self.stdout.write("")
            db_grad_total = (
                CohortUser.objects.filter(cohort=cohort, role=STUDENT, educational_status=GRADUATED)
                .exclude(cohort__stage="DELETED")
                .count()
            )
            self.stdout.write(
                self.style.NOTICE(
                    f"  [dry-run] Resumen cohort {cohort.slug!r}: "
                    f"graduaría a {graduated_new} STUDENT(s); "
                    f"{already_graduated_complete} ya GRADUATED con lecciones+ejs al 100% (sin cambio de estado)."
                )
            )
            if not skip_certificates:
                cert_planned_union = db_grad_total + graduated_new
                self.stdout.write(
                    self.style.NOTICE(
                        f"  [dry-run] Tras ejecutar escritura: ~{cert_planned_union} intento(s) de certificado "
                        f"(GRADUATED en BD hoy={db_grad_total} + nuevos graduados={graduated_new}). "
                        f"*La lista de arriba desglosa cada email."
                    )
                )
