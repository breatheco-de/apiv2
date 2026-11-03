"""Move FULLY_PAID stock that was issued two renew periods ahead back by one period."""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from breathecode.payments.actions import calculate_relative_delta
from breathecode.payments.models import Consumable, PlanFinancing, ServiceStockScheduler

# The old seed used timezone.now() a few seconds after PlanFinancing.created_at.
MATCH_TOLERANCE = timedelta(minutes=15)
RENEW_UNITS = {"DAY", "WEEK", "MONTH", "YEAR"}


def _add_periods(start: datetime, delta, times: int) -> datetime:
    value = start
    for _ in range(times):
        value = value + delta
    return value


def _close(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= MATCH_TOLERANCE


class Command(BaseCommand):
    help = (
        "List FULLY_PAID schedulers whose only consumable is still inside the extra renew "
        "period, and move that consumable and the scheduler back to one period. "
        "Dry-run unless --apply is passed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Save the new valid_until. Without this flag the command only prints the plan.",
        )
        parser.add_argument("--email", type=str, default=None, help="Limit to a user email")
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            default=None,
            help="Limit to a single PlanFinancing id",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        schedulers = (
            ServiceStockScheduler.objects.filter(
                plan_handler__plan_financing__status=PlanFinancing.Status.FULLY_PAID,
            )
            .select_related(
                "plan_handler__plan_financing__user",
                "plan_handler__handler__service_item__service",
            )
            .annotate(consumable_count=Count("consumables"))
            .order_by("id")
        )
        if options["email"]:
            schedulers = schedulers.filter(plan_handler__plan_financing__user__email__iexact=options["email"])
        if options["plan_financing_id"]:
            schedulers = schedulers.filter(plan_handler__plan_financing_id=options["plan_financing_id"])

        updated = 0
        skipped = 0
        for scheduler in schedulers:
            fix = self._fix_for(scheduler)
            if fix is None:
                skipped += 1
                continue

            consumable, corrected = fix
            financing = scheduler.plan_handler.plan_financing
            service_item = scheduler.plan_handler.handler.service_item
            self.stdout.write(
                f"scheduler={scheduler.id} financing={financing.id} user={financing.user.email} "
                f"service_item={service_item.id} renew={service_item.renew_at} {service_item.renew_at_unit}"
            )
            self.stdout.write(f"  consumable={consumable.id} {consumable.valid_until} -> {corrected}")
            if apply:
                consumable.valid_until = corrected
                consumable.save(update_fields=["valid_until"])
                scheduler.valid_until = corrected
                scheduler.save(update_fields=["valid_until"])
            updated += 1

        if apply:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated} scheduler(s). Skipped {skipped}."))
            return

        self.stdout.write(f"Would update {updated} scheduler(s). Skipped {skipped}. Pass --apply to save.")

    def _fix_for(self, scheduler: ServiceStockScheduler) -> tuple[Consumable, datetime] | None:
        """Return the consumable and the corrected date, or None when this row must stay."""
        if scheduler.consumable_count != 1:
            return None

        financing = scheduler.plan_handler.plan_financing
        service_item = scheduler.plan_handler.handler.service_item
        if service_item.renew_at_unit not in RENEW_UNITS or not service_item.renew_at:
            return None

        consumable = scheduler.consumables.first()
        if consumable is None or consumable.valid_until is None or scheduler.valid_until is None:
            return None

        if financing.plan_expires_at and (
            consumable.valid_until == financing.plan_expires_at or scheduler.valid_until == financing.plan_expires_at
        ):
            return None

        delta = calculate_relative_delta(service_item.renew_at, service_item.renew_at_unit)
        one_period = _add_periods(financing.created_at, delta, 1)
        two_periods = _add_periods(financing.created_at, delta, 2)
        if not _close(consumable.valid_until, two_periods) or not _close(scheduler.valid_until, two_periods):
            return None

        # The doubled period already ended. Leave historical stock alone.
        if consumable.valid_until <= timezone.now():
            return None

        return consumable, one_period
