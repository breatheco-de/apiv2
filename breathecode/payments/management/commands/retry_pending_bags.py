from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.payments.actions import retry_pending_bag

from ...models import Bag


class Command(BaseCommand):
    help = "Retry pending bags that have not been delivered"

    def handle(self, *args, **options):
        now = timezone.now()
        bags = Bag.objects.filter(was_delivered=False, created_at__lte=now - timedelta(minutes=10), status="PAID")
        hm_processed = 0
        hm_failed = 0

        for bag in bags:
            result = retry_pending_bag(bag)
            if result == "scheduled":
                hm_processed += 1
            elif result == "done":
                hm_processed += 1
            else:
                hm_failed += 1

        total = hm_processed + hm_failed
        self.stdout.write(
            self.style.SUCCESS(
                f"Rescheduled {total} bags where {hm_processed} were processed and {hm_failed} were failed."
            )
        )
