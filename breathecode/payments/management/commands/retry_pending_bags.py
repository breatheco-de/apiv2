from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ... import tasks
from ...models import Bag, Invoice


# renew the credits every 1 hours
class Command(BaseCommand):
    help = "Renew credits"

    def handle(self, *args, **options):
        now = timezone.now()
        bags = Bag.objects.filter(was_delivered=False, created_at__lte=now - timedelta(minutes=10), status="PAID")
        hm_processed = 0
        hm_failed = 0

        for bag in bags:
            invoice: Invoice | None = bag.invoice_set.first()
            if invoice is None:
                continue

            if bag.how_many_installments > 0:
                tasks.build_plan_financing.delay(bag.id, invoice.id)

            elif invoice.amount > 0:
                tasks.build_subscription.delay(bag.id, invoice.id)

            else:
                tasks.build_free_subscription.delay(bag.id, invoice.id)

        total = hm_processed + hm_failed
        self.stdout.write(
            self.style.SUCCESS(
                f"Rescheduled {total} bags where {hm_processed} were processed and {hm_failed} were failed."
            )
        )
