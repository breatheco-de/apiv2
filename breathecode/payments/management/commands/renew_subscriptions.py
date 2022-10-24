from datetime import timedelta
from django.core.management.base import BaseCommand
from breathecode.payments import tasks

from breathecode.payments.actions import payWithStripe
from ...models import Consumable, Subscription, Credit
from django.utils import timezone
from breathecode.notify import actions as notify_actions

from dateutil.relativedelta import relativedelta


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = 'Renew credits'

    def handle(self, *args, **options):
        utc_now = timezone.now()
        subscriptions = Subscription.objects.filter(
            valid_until__lte=utc_now, renew_credits_at__lte=utc_now +
            timedelta(hours=2)).exclude(status='CANCELLED').exclude(status='DEPRECATED')

        for subscription in subscriptions:
            tasks.renew_subscription.delay(subscription.id, utc_now)
