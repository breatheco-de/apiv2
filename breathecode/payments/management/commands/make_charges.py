from datetime import timedelta
from django.core.management.base import BaseCommand
from breathecode.payments import tasks

from ...models import PlanFinancing, Subscription
from django.utils import timezone


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = 'Renew credits'

    def handle(self, *args, **options):
        utc_now = timezone.now()
        subscriptions = Subscription.objects.filter(valid_until__lte=utc_now + timedelta(days=1)).exclude(
            status='CANCELLED').exclude(status='DEPRECATED').exclude(status='FREE_TRIAL')

        plan_financings = PlanFinancing.objects.filter(valid_until__lte=utc_now + timedelta(days=1)).exclude(
            status='CANCELLED').exclude(status='DEPRECATED').exclude(status='FREE_TRIAL')

        for subscription in subscriptions:
            tasks.charge_subscription.delay(subscription.id)

        for plan_financing in plan_financings:
            tasks.charge_plan_financing.delay(plan_financing.id)
