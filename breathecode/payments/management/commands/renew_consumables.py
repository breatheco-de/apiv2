from datetime import timedelta
from django.core.management.base import BaseCommand
from ...models import PlanFinancing, ServiceStockScheduler, Subscription
from django.utils import timezone

from ... import tasks


# renew the credits every 1 hours
class Command(BaseCommand):
    help = "Renew credits"

    def handle(self, *args, **options):
        self.utc_now = timezone.now()
        self.subscriptions()
        self.plan_financing()

    def subscriptions(self):
        subscriptions = Subscription.objects.filter().exclude(status="CANCELLED").exclude(status="DEPRECATED")

        if subscriptions.count() == 0:
            return

        subscription_ids = list(subscriptions.values_list("id", flat=True))

        no_need_to_renew = (
            ServiceStockScheduler.objects.filter(consumables__valid_until__gte=self.utc_now + timedelta(hours=2))
            .exclude(plan_handler__subscription__status="CANCELLED")
            .exclude(plan_handler__subscription__status="DEPRECATED")
            .exclude(plan_handler__subscription__status="PAYMENT_ISSUE")
        )

        for subscription in no_need_to_renew:
            subscription_ids.remove(subscription.id)

        for subscription_id in subscription_ids:
            tasks.renew_subscription_consumables.delay(subscription_id)

    def plan_financing(self):
        plan_financings = (
            PlanFinancing.objects.filter().exclude(status__in=["CANCELLED", "DEPRECATED"]).only("id", "user")
        )

        if plan_financings.count() == 0:
            return

        plan_financing_ids = list(plan_financings.values_list("id", flat=True))

        no_need_to_renew = ServiceStockScheduler.objects.filter(
            consumables__valid_until__gte=self.utc_now + timedelta(hours=2)
        ).exclude(plan_handler__plan_financing__status__in=["CANCELLED", "DEPRECATED", "PAYMENT_ISSUE"])

        for plan_financing in no_need_to_renew:
            plan_financing_ids.remove(plan_financing.id)

        for plan_financing_id in plan_financing_ids:
            tasks.renew_plan_financing_consumables.delay(plan_financing_id)
