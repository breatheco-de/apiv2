import os
from django.core.management.base import BaseCommand
from breathecode.provisioning.models import ProvisioningBill

from breathecode.provisioning.tasks import archive_provisioning_bill
from dateutil.relativedelta import relativedelta
from django.utils import timezone

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


# archive_provisioning_bills
class Command(BaseCommand):
    help = "Archive older provisioning bills"

    def handle(self, *args, **options):

        now = timezone.now()
        ids = ProvisioningBill.objects.filter(
            status="PAID", paid_at__lte=now - relativedelta(months=1), archived_at__isnull=True
        ).values_list("id", flat=True)

        for id in ids:
            archive_provisioning_bill.delay(id)

        if ids:
            msg = self.style.SUCCESS(f"Cleaning {', '.join([str(id) for id in ids])} provisioning bills")

        else:
            msg = self.style.SUCCESS("No provisioning bills to clean")

        self.stdout.write(self.style.SUCCESS(msg))
