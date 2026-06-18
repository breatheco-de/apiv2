"""Set finantial_status to UP_TO_DATE for ACTIVE CohortUsers whose finantial_status is null or empty."""

from __future__ import annotations

from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from breathecode.admissions.models import ACTIVE, Cohort, CohortUser, UP_TO_DATE


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


def filter_users_with_active_plan_financing_or_subscription(qs):
    """Only CohortUsers whose user has active PlanFinancing or Subscription."""
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


def cohort_users_active_null_financial(
    cohort: Cohort,
    *,
    role: str | None,
    created_on_or_after: datetime | None = None,
    require_active_payment: bool = False,
):
    """
    ACTIVE CohortUsers with finantial_status null or empty string.
    Rows with LATE, FULLY_PAID, UP_TO_DATE, etc. are excluded.
    """
    qs = (
        CohortUser.objects.filter(cohort=cohort, educational_status=ACTIVE)
        .filter(Q(finantial_status__isnull=True) | Q(finantial_status=""))
        .exclude(cohort__stage="DELETED")
        .select_related("user", "cohort")
        .order_by("id")
    )
    if created_on_or_after is not None:
        qs = qs.filter(created_at__gte=created_on_or_after)
    if role:
        qs = qs.filter(role=role.strip().upper())
    if require_active_payment:
        qs = filter_users_with_active_plan_financing_or_subscription(qs)
    return qs


def ordered_micro_cohorts(macro: Cohort) -> list[Cohort]:
    qs = macro.micro_cohorts.exclude(stage="DELETED").all()
    micros_by_id: dict[int, Cohort] = {c.id: c for c in qs}
    if not micros_by_id:
        return []

    raw = (macro.cohorts_order or "").strip()
    if not raw:
        return sorted(micros_by_id.values(), key=lambda c: c.id)

    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            cid = int(part)
        except ValueError:
            continue
        if cid in micros_by_id and cid not in ids:
            ids.append(cid)

    for cid in sorted(micros_by_id.keys()):
        if cid not in ids:
            ids.append(cid)

    return [micros_by_id[cid] for cid in ids]


class Command(BaseCommand):
    help = (
        "Set finantial_status to UP_TO_DATE for CohortUsers with educational_status ACTIVE "
        "and finantial_status null or empty. Rows with any other finantial_status are not changed. "
        "Target one cohort (--cohort-id/--cohort-slug) or a macro and all its micros "
        "(--macro-cohort-id/--macro-cohort-slug)."
    )

    def add_arguments(self, parser):
        cohort_group = parser.add_mutually_exclusive_group(required=True)
        cohort_group.add_argument("--cohort-id", type=int, help="Cohort primary key")
        cohort_group.add_argument("--cohort-slug", type=str, help="Cohort slug (unique)")
        cohort_group.add_argument("--macro-cohort-id", type=int, help="Macro cohort primary key (macro + all micros)")
        cohort_group.add_argument("--macro-cohort-slug", type=str, help="Macro cohort slug (macro + all micros)")

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
                "With --cohort-id/--cohort-slug on a macro cohort: also update linked micro cohorts. "
                "Ignored when using --macro-cohort-id/--macro-cohort-slug (micros are always included)."
            ),
        )

        parser.add_argument(
            "--require-active-payment",
            action="store_true",
            help=(
                "Only update users with PlanFinancing (ACTIVE or FULLY_PAID) or an active Subscription. "
                "By default all matching ACTIVE rows with null finantial_status are updated."
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
        role = options["role"]
        since_created = (
            parse_created_on_or_after(options["created_on_or_after"])
            if options.get("created_on_or_after")
            else None
        )
        require_active_payment = options["require_active_payment"]
        dry_run = options["dry_run"]

        macro_id = options.get("macro_cohort_id")
        macro_slug = options.get("macro_cohort_slug")

        if macro_id is not None or macro_slug is not None:
            macro = self._resolve_macro(macro_id, macro_slug)
            cohorts = [macro] + ordered_micro_cohorts(macro)
            if len(cohorts) == 1:
                self.stdout.write(
                    self.style.WARNING(
                        f"Macro cohort '{macro.slug}' has no linked micro cohorts; only the macro row is scanned."
                    )
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Macro cohort: {macro.name} (id={macro.id}) + {len(cohorts) - 1} micro cohort(s)"
                    )
                )
            self._process_cohorts(cohorts, role, since_created, require_active_payment, dry_run)
            return

        cohort = self._resolve_cohort(options)
        cohorts = [cohort]
        if options["include_micro_cohorts"]:
            cohorts.extend(ordered_micro_cohorts(cohort))

        self._process_cohorts(cohorts, role, since_created, require_active_payment, dry_run)

    def _resolve_cohort(self, options) -> Cohort:
        cohort_id = options.get("cohort_id")
        if cohort_id is not None:
            cohort = Cohort.objects.filter(id=cohort_id).first()
            if not cohort:
                raise CommandError(f"No cohort found with id={cohort_id}")
            return cohort

        slug = options["cohort_slug"].strip()
        cohort = Cohort.objects.filter(slug=slug).first()
        if not cohort:
            raise CommandError(f"No cohort found with slug={slug!r}")
        return cohort

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

    def _process_cohorts(
        self,
        cohorts: list[Cohort],
        role: str | None,
        since_created: datetime | None,
        require_active_payment: bool,
        dry_run: bool,
    ) -> None:
        total = 0
        updated = 0

        self.stdout.write(
            self.style.NOTICE(
                "  Rule: educational_status=ACTIVE and finantial_status is null or empty → UP_TO_DATE"
            )
        )
        if require_active_payment:
            self.stdout.write(
                self.style.NOTICE(
                    "  Payment filter: user must have PlanFinancing (ACTIVE/FULLY_PAID) or active Subscription."
                )
            )
        else:
            self.stdout.write(self.style.NOTICE("  Payment filter: off"))

        if since_created is not None:
            self.stdout.write(
                self.style.NOTICE(f"  created_at filter: CohortUser.created_at >= {since_created.isoformat()}")
            )

        for cohort in cohorts:
            if cohort.stage == "DELETED":
                self.stdout.write(self.style.WARNING(f"  SKIP cohort {cohort.slug!r}: DELETED"))
                continue

            rows = list(
                cohort_users_active_null_financial(
                    cohort,
                    role=role,
                    created_on_or_after=since_created,
                    require_active_payment=require_active_payment,
                )
            )
            if not rows:
                continue

            self.stdout.write(
                self.style.NOTICE(
                    f"\nCohort: {cohort.name} (id={cohort.id}, slug={cohort.slug}) — {len(rows)} match(es)"
                )
            )

            for cu in rows:
                total += 1
                self.stdout.write(
                    f"  CohortUser id={cu.id} user_id={cu.user_id} email={cu.user.email} "
                    f"role={cu.role} finantial_status={cu.finantial_status!r}"
                )
                if dry_run:
                    continue

                cu.finantial_status = UP_TO_DATE
                cu.save(update_fields=["finantial_status", "updated_at"])
                updated += 1

        if total == 0:
            self.stdout.write(self.style.WARNING("Nothing to update."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDry run: would update {total} row(s)."))
            return

        self.stdout.write(self.style.SUCCESS(f"\nUpdated finantial_status to UP_TO_DATE for {updated} CohortUser(s)."))
