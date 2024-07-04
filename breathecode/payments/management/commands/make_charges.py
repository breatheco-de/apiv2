from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q
from django.utils import timezone

from breathecode.payments import tasks

from ...models import PlanFinancing, Subscription


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = "Renew credits"

    def handle(self, *args, **options):
        utc_now = timezone.now()
        statuses = ["CANCELLED", "DEPRECATED", "FREE_TRIAL", "EXPIRED"]

        avoid_expire_these_statuses = (
            Q(status="EXPIRED")
            | Q(status="ERROR")
            | Q(status="PAYMENT_ISSUE")
            | Q(status="FULLY_PAID")
            | Q(status="FREE_TRIAL")
            | Q(status="CANCELLED")
            | Q(status="DEPRECATED")
        )

        subscription_args = (Q(valid_until__isnull=True) | Q(valid_until__gt=utc_now),)
        financing_args = (Q(plan_expires_at__isnull=True) | Q(plan_expires_at__gt=utc_now),)
        params = {
            "next_payment_at__lte": utc_now + timedelta(days=1),
        }

        Subscription.objects.filter(
            Q(valid_until__gte=utc_now) | Q(valid_until__isnull=True),
            next_payment_at__lte=utc_now - timedelta(days=7),
            status="PAYMENT_ISSUE",
        ).update(status="EXPIRED")

        Subscription.objects.filter(valid_until__lte=utc_now).exclude(avoid_expire_these_statuses).update(
            status="EXPIRED"
        )

        PlanFinancing.objects.filter(plan_expires_at__lte=utc_now).exclude(avoid_expire_these_statuses).update(
            status="EXPIRED"
        )

        subscriptions = Subscription.objects.filter(*subscription_args, **params)
        plan_financings = PlanFinancing.objects.filter(*financing_args, **params)

        for status in statuses:
            subscriptions = subscriptions.exclude(status=status)

        statuses.append("FULLY_PAID")

        for status in statuses:
            plan_financings = plan_financings.exclude(status=status)

        for subscription in subscriptions:
            tasks.charge_subscription.delay(subscription.id)

        for plan_financing in plan_financings:
            tasks.charge_plan_financing.delay(plan_financing.id)
