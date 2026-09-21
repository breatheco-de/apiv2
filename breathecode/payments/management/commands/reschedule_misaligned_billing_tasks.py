from logging import getLogger

from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone
from task_manager.django.models import ScheduledTask

from breathecode.payments.actions import reschedule_billing_tasks
from breathecode.payments.models import PlanFinancing, Subscription

logger = getLogger(__name__)

TASK_MODULE = "breathecode.payments.tasks"
CHARGE_SUBSCRIPTION = "charge_subscription"
CHARGE_PLAN_FINANCING = "charge_plan_financing"

SUBSCRIPTION_STATUSES = {
    Subscription.Status.ACTIVE,
    Subscription.Status.PAYMENT_ISSUE,
    Subscription.Status.ERROR,
}

PLAN_FINANCING_STATUSES = {
    PlanFinancing.Status.ACTIVE,
    PlanFinancing.Status.PAYMENT_ISSUE,
    PlanFinancing.Status.ERROR,
}


class Command(BaseCommand):
    help = (
        "Find active billable subscriptions/plan financings with next_payment_at in the "
        "future whose PENDING charge ETA is before next_payment_at, or (non-seat) that "
        "are missing a charge schedule; rebuild via reschedule_billing_tasks. "
        "Skips free subscriptions (plans with no positive price)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List affected entities without calling reschedule_billing_tasks",
        )
        parser.add_argument("--email", type=str, default=None, help="Limit to a user email")
        parser.add_argument(
            "--subscription-id",
            type=int,
            default=None,
            help="Limit to a single Subscription id",
        )
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            default=None,
            help="Limit to a single PlanFinancing id",
        )

    def handle(self, *args, **options):
        utc_now = timezone.now()
        dry_run = options["dry_run"]
        email = options.get("email")
        subscription_id = options.get("subscription_id")
        plan_financing_id = options.get("plan_financing_id")

        logger.info(
            "Starting reschedule_misaligned_billing_tasks dry_run=%s email=%s "
            "subscription_id=%s plan_financing_id=%s",
            dry_run,
            email,
            subscription_id,
            plan_financing_id,
        )

        targets: dict[tuple[str, int], str] = {}
        self._collect_subscriptions(
            targets,
            utc_now=utc_now,
            email=email,
            subscription_id=subscription_id,
        )
        self._collect_plan_financings(
            targets,
            utc_now=utc_now,
            email=email,
            plan_financing_id=plan_financing_id,
        )

        fixed = 0
        for (kind, entity_id), reason in sorted(targets.items()):
            self.stdout.write(f"{kind}_id={entity_id} reason={reason}")
            if dry_run:
                continue

            if kind == "subscription":
                reschedule_billing_tasks(subscription_id=entity_id)
            else:
                reschedule_billing_tasks(plan_financing_id=entity_id)
            fixed += 1
            logger.info("Rescheduled %s_id=%s reason=%s", kind, entity_id, reason)

        action = "Would reschedule" if dry_run else "Rescheduled"
        self.stdout.write(self.style.SUCCESS(f"{action} {len(targets)} billing schedule(s)."))
        logger.info(
            "Finished reschedule_misaligned_billing_tasks dry_run=%s count=%s fixed=%s",
            dry_run,
            len(targets),
            fixed,
        )

    def _subscription_is_billable(self, subscription: Subscription) -> bool:
        """True when any plan has a positive catalog price (excludes free ACTIVE renewables)."""
        for plan in subscription.plans.all():
            for price in (
                plan.price_per_month,
                plan.price_per_quarter,
                plan.price_per_half,
                plan.price_per_year,
            ):
                if price is not None and price > 0:
                    return True
        return False

    def _collect_subscriptions(
        self,
        targets: dict[tuple[str, int], str],
        *,
        utc_now,
        email: str | None,
        subscription_id: int | None,
    ) -> None:
        """
        Flag subscriptions that need reschedule_billing_tasks:

        - PENDING charge ETA before next_payment_at (truncated-days bug), or
        - no PENDING charge at all (except seat-based subs, which skip post-charge schedule).

        Only considers billable ACTIVE/PAYMENT_ISSUE/ERROR with next_payment_at still in
        the future (overdue catch-up belongs to make_charges / retry_overdue_staff_auto_charges).
        Free subscriptions (no positive plan price) are skipped — they never need charge tasks.
        """
        pending_etas = self._pending_charge_etas(CHARGE_SUBSCRIPTION)

        qs = (
            Subscription.objects.filter(
                status__in=SUBSCRIPTION_STATUSES,
                next_payment_at__gt=utc_now,
            )
            .select_related("user", "seat_service_item")
            .prefetch_related("plans")
        )
        if email:
            qs = qs.filter(user__email__iexact=email)
        if subscription_id is not None:
            qs = qs.filter(pk=subscription_id)

        for subscription in qs:
            if not self._subscription_is_billable(subscription):
                continue

            etas = pending_etas.get(subscription.id)
            if etas:
                if any(eta < subscription.next_payment_at for eta in etas):
                    targets[("subscription", subscription.id)] = "eta_before_next_payment_at"
                continue

            # Seat-based subscriptions intentionally skip charge reschedule after charge.
            if subscription.seat_service_item and subscription.seat_service_item.how_many > 0:
                continue

            targets[("subscription", subscription.id)] = "missing_charge_schedule"

    def _collect_plan_financings(
        self,
        targets: dict[tuple[str, int], str],
        *,
        utc_now,
        email: str | None,
        plan_financing_id: int | None,
    ) -> None:
        """
        Flag plan financings that need reschedule_billing_tasks:

        - PENDING charge ETA before next_payment_at (truncated-days bug), or
        - no PENDING charge and installments still remaining.

        Only ACTIVE/PAYMENT_ISSUE/ERROR with next_payment_at in the future; overdue
        created_by_admin catch-up is handled by retry_overdue_staff_auto_charges.
        """
        pending_etas = self._pending_charge_etas(CHARGE_PLAN_FINANCING)

        qs = PlanFinancing.objects.filter(
            status__in=PLAN_FINANCING_STATUSES,
            next_payment_at__gt=utc_now,
            how_many_installments__gt=F("installments_paid"),
        ).select_related("user")
        if email:
            qs = qs.filter(user__email__iexact=email)
        if plan_financing_id is not None:
            qs = qs.filter(pk=plan_financing_id)

        for plan_financing in qs.iterator():
            etas = pending_etas.get(plan_financing.id)
            if etas:
                if any(eta < plan_financing.next_payment_at for eta in etas):
                    targets[("plan_financing", plan_financing.id)] = "eta_before_next_payment_at"
                continue

            targets[("plan_financing", plan_financing.id)] = "missing_charge_schedule"

    def _pending_charge_etas(self, task_name: str) -> dict[int, list]:
        """Map entity id → PENDING charge ETAs for that charge task."""
        by_entity: dict[int, list] = {}
        qs = ScheduledTask.objects.filter(
            task_module=TASK_MODULE,
            task_name=task_name,
            status="PENDING",
        ).only("arguments", "eta")
        for scheduled in qs.iterator():
            arguments = scheduled.arguments
            if not isinstance(arguments, dict):
                continue
            args = arguments.get("args") or []
            if not args:
                continue
            try:
                entity_id = int(args[0])
            except (TypeError, ValueError):
                continue
            by_entity.setdefault(entity_id, []).append(scheduled.eta)
        return by_entity
