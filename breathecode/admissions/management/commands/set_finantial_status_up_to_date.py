"""Set finantial_status to UP_TO_DATE for ACTIVE CohortUsers without a financial status."""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from breathecode.admissions.models import ACTIVE, Cohort, CohortUser, UP_TO_DATE


def cohort_users_missing_financial(cohort: Cohort, *, role: str | None):
    """CohortUsers in this cohort that are ACTIVE and have empty finantial_status."""
    qs = (
        CohortUser.objects.filter(cohort=cohort, educational_status=ACTIVE)
        .filter(Q(finantial_status__isnull=True) | Q(finantial_status=""))
        .select_related("user", "cohort")
        .order_by("id")
    )
    if role:
        qs = qs.filter(role=role.strip().upper())
    return qs


class Command(BaseCommand):
    help = (
        "For a given cohort, list CohortUsers with no finantial_status "
        "(null or empty) and educational_status ACTIVE, and set finantial_status to UP_TO_DATE. "
        "If --include-micro-cohorts is set and this cohort links micro cohorts (macro), "
        "also updates matching CohortUsers for the same users in those micro cohorts."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--cohort-id", type=int, help="Cohort primary key")
        group.add_argument("--cohort-slug", type=str, help="Cohort slug (unique)")

        parser.add_argument(
            "--role",
            type=str,
            default=None,
            help="If set (e.g. STUDENT), only include CohortUsers with this role.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print matching CohortUsers without updating the database.",
        )

        parser.add_argument(
            "--include-micro-cohorts",
            action="store_true",
            help=(
                "If this cohort lists micro cohorts, also apply the same logic for CohortUsers in those "
                "micro cohorts, but only for user_ids that qualify on this (macro) cohort."
            ),
        )

    def handle(self, *args, **options):
        if options["cohort_id"] is not None:
            cohort = Cohort.objects.filter(id=options["cohort_id"]).first()
            if not cohort:
                raise CommandError(f"No cohort found with id={options['cohort_id']}")
        else:
            slug = options["cohort_slug"].strip()
            cohort = Cohort.objects.filter(slug=slug).first()
            if not cohort:
                raise CommandError(f"No cohort found with slug={slug!r}")

        role = options["role"]

        macro_qs = cohort_users_missing_financial(cohort, role=role)

        micro_qs = CohortUser.objects.none()
        if options["include_micro_cohorts"]:
            micro_ids = list(cohort.micro_cohorts.values_list("pk", flat=True))
            if micro_ids:
                micro_qs = (
                    CohortUser.objects.filter(
                        cohort_id__in=micro_ids,
                        user_id__in=macro_qs.values("user_id"),
                        educational_status=ACTIVE,
                    )
                    .filter(Q(finantial_status__isnull=True) | Q(finantial_status=""))
                    .select_related("user", "cohort")
                    .order_by("cohort_id", "id")
                )
                if role:
                    micro_qs = micro_qs.filter(role=role.strip().upper())

        macro_rows = list(macro_qs)
        micro_rows = list(micro_qs)
        macro_count = len(macro_rows)
        micro_count = len(micro_rows)
        total = macro_count + micro_count
        rows = macro_rows + micro_rows

        self.stdout.write(self.style.NOTICE(f"Cohort: {cohort.name} (id={cohort.id}, slug={cohort.slug})"))
        if options["include_micro_cohorts"]:
            micro_linked = cohort.micro_cohorts.count()
            self.stdout.write(
                self.style.NOTICE(
                    f"  Include micro cohorts: yes — linked micro cohorts: {micro_linked} "
                    f"(matches restricted to macro-qualified user_ids)."
                )
            )
        else:
            self.stdout.write(self.style.NOTICE("  Include micro cohorts: no (macro-only)."))
        self.stdout.write(self.style.NOTICE(f"  Matches on this cohort (macro/root): {macro_count}"))
        self.stdout.write(self.style.NOTICE(f"  Matches on linked micro cohorts: {micro_count}"))
        self.stdout.write(self.style.NOTICE(f"  Total rows: {total}"))

        if total == 0:
            self.stdout.write(self.style.WARNING("Nothing to update."))
            return

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: no rows will be updated."))

        for cu in rows:
            line = (
                f"  cohort={cu.cohort.slug} CohortUser id={cu.id} user_id={cu.user_id} "
                f"email={cu.user.email} role={cu.role} "
                f"educational_status={cu.educational_status} finantial_status={cu.finantial_status!r}"
            )
            self.stdout.write(line)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"\nDry run ended: would update {total} row(s)."))
            return

        updated = 0
        for cu in rows:
            cu.finantial_status = UP_TO_DATE
            cu.save()
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated finantial_status to UP_TO_DATE for {updated} CohortUser(s)."))
