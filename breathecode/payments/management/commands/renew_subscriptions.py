from datetime import timedelta
from django.core.management.base import BaseCommand
from breathecode.payments import tasks

from ...models import Subscription
from django.utils import timezone


# renew the subscriptions every 1 hours
class Command(BaseCommand):
    help = 'Renew credits'

    def handle(self, *args, **options):
        utc_now = timezone.now()
        subscriptions = Subscription.objects.filter(valid_until__lte=utc_now + timedelta(hours=2)).exclude(
            status='CANCELLED').exclude(status='DEPRECATED')

        for subscription in subscriptions:
            tasks.renew_subscription.delay(subscription.id, utc_now)
