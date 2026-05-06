"""Set finantial_status to UP_TO_DATE for ACTIVE/GRADUATED CohortUsers without a financial status."""

from __future__ import annotations

from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from breathecode.admissions.models import ACTIVE, Cohort, CohortUser, GRADUATED, UP_TO_DATE

_ELIGIBLE_EDUCATIONAL = [ACTIVE, GRADUATED]


def filter_users_with_active_plan_financing_or_subscription(qs):
    """
    Only CohortUsers whose user has at least one PlanFinancing in ACTIVE or FULLY_PAID,
    or at least one Subscription in ACTIVE.
    """
    from breathecode.payments.models import PlanFinancing, Subscription

    S = PlanFinancing.Status
    pf_exists = PlanFinancing.objects.filter(
        user_id=OuterRef("user_id"),
        status__in=[S.ACTIVE, S.FULLY_PAID],
    )
    sub_exists = Subscription.objects.filter(
        user_id=OuterRef("user_id"),
        status=Subscription.Status.ACTIVE,
    )
    return qs.annotate(
        _has_pf_ok=Exists(pf_exists),
        _has_sub_ok=Exists(sub_exists),
    ).filter(Q(_has_pf_ok=True) | Q(_has_sub_ok=True))


def parse_created_on_or_after(raw: str):
    """ISO date (YYYY-MM-DD) or datetime; naive values use the current timezone."""
    s = raw.strip()
    dt = parse_datetime(s)
    if dt is not None:
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    d = parse_date(s)
    if d is not None:
        return timezone.make_aware(datetime.combine(d, time.min), timezone.get_current_timezone())
    raise CommandError(
        f"Invalid date/datetime {raw!r}. Use ISO date YYYY-MM-DD or datetime, e.g. 2026-01-15T12:00:00."
    )


def cohort_users_missing_financial(
    cohort: Cohort, *, role: str | None, created_on_or_after: datetime | None = None
):
    """CohortUsers in this cohort that are ACTIVE or GRADUATED and have empty finantial_status."""
    qs = (
        CohortUser.objects.filter(cohort=cohort, educational_status__in=_ELIGIBLE_EDUCATIONAL)
        .filter(Q(finantial_status__isnull=True) | Q(finantial_status=""))
        .select_related("user", "cohort")
        .order_by("id")
    )
    if created_on_or_after is not None:
        qs = qs.filter(created_at__gte=created_on_or_after)
    if role:
        qs = qs.filter(role=role.strip().upper())
    return filter_users_with_active_plan_financing_or_subscription(qs)


def macro_enrolled_user_ids(cohort: Cohort, *, role: str | None):
    """user_ids with an ACTIVE/GRADUATED CohortUser on this cohort (scopes which micro rows we touch)."""
    qs = CohortUser.objects.filter(cohort=cohort, educational_status__in=_ELIGIBLE_EDUCATIONAL)
    if role:
        qs = qs.filter(role=role.strip().upper())
    return qs.values("user_id")


class Command(BaseCommand):
    help = (
        "Set finantial_status to UP_TO_DATE for CohortUsers with no finantial_status "
        "(null or empty) and educational_status ACTIVE or GRADUATED. "
        "You must pass the cohort with --cohort-id or --cohort-slug. "
        "Use --include-micro-cohorts to also update linked micro cohorts for users on that macro. "
        "Optional --created-on-or-after limits to CohortUser rows whose created_at is on or after that instant. "
        "Only users with at least one PlanFinancing (ACTIVE or FULLY_PAID) or an active Subscription are included."
    )

    def add_arguments(self, parser):
        cohort_group = parser.add_mutually_exclusive_group(required=True)
        cohort_group.add_argument("--cohort-id", type=int, help="Cohort primary key")
        cohort_group.add_argument("--cohort-slug", type=str, help="Cohort slug (unique)")

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
                "micro cohorts, for any user who has an ACTIVE or GRADUATED CohortUser on this macro cohort "
                "(macro finantial_status may already be set)."
            ),
        )
        parser.add_argument(
            "--created-on-or-after",
            type=str,
            default=None,
            metavar="DATE_OR_DATETIME",
            help=(
                "Only consider CohortUser rows with created_at >= this value "
                "(ISO date YYYY-MM-DD or datetime). Omit to apply no created_at filter."
            ),
        )

    def handle(self, *args, **options):
        cohort_id = options.get("cohort_id")
        cohort_slug = options.get("cohort_slug")

        if cohort_id is not None:
            cohort = Cohort.objects.filter(id=cohort_id).first()
            if not cohort:
                raise CommandError(f"No cohort found with id={cohort_id}")
        else:
            slug = cohort_slug.strip()
            cohort = Cohort.objects.filter(slug=slug).first()
            if not cohort:
                raise CommandError(f"No cohort found with slug={slug!r}")

        role = options["role"]
        since_created = (
            parse_created_on_or_after(options["created_on_or_after"])
            if options.get("created_on_or_after")
            else None
        )

        macro_qs = cohort_users_missing_financial(cohort, role=role, created_on_or_after=since_created)

        micro_qs = CohortUser.objects.none()
        if options["include_micro_cohorts"]:
            micro_ids = list(cohort.micro_cohorts.values_list("pk", flat=True))
            if micro_ids:
                micro_qs = (
                    CohortUser.objects.filter(
                        cohort_id__in=micro_ids,
                        user_id__in=macro_enrolled_user_ids(cohort, role=role),
                        educational_status__in=_ELIGIBLE_EDUCATIONAL,
                    )
                    .filter(Q(finantial_status__isnull=True) | Q(finantial_status=""))
                    .select_related("user", "cohort")
                    .order_by("cohort_id", "id")
                )
                if since_created is not None:
                    micro_qs = micro_qs.filter(created_at__gte=since_created)
                if role:
                    micro_qs = micro_qs.filter(role=role.strip().upper())
                micro_qs = filter_users_with_active_plan_financing_or_subscription(micro_qs)

        macro_rows = list(macro_qs)
        micro_rows = list(micro_qs)
        macro_count = len(macro_rows)
        micro_count = len(micro_rows)
        total = macro_count + micro_count
        rows = macro_rows + micro_rows

        self.stdout.write(self.style.NOTICE(f"Cohort: {cohort.name} (id={cohort.id}, slug={cohort.slug})"))
        if since_created is not None:
            self.stdout.write(
                self.style.NOTICE(f"  created_at filter: CohortUser.created_at >= {since_created.isoformat()}")
            )
        self.stdout.write(
            self.style.NOTICE(
                "  Payment filter: user has PlanFinancing status ACTIVE or FULLY_PAID, "
                "or Subscription status ACTIVE."
            )
        )
        if options["include_micro_cohorts"]:
            micro_linked = cohort.micro_cohorts.count()
            self.stdout.write(
                self.style.NOTICE(
                    f"  Include micro cohorts: yes — linked micro cohorts: {micro_linked} "
                    f"(micro rows scoped to users with ACTIVE/GRADUATED on this macro)."
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
