import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from breathecode.provisioning.tasks import archive_provisioning_bill
from ...models import ProvisioningBill, Task
from ...actions import sync_student_tasks
from breathecode.admissions.models import CohortUser
from django.db.models import Count
from dateutil.relativedelta import relativedelta
from django.utils import timezone

HOST = os.environ.get('OLD_BREATHECODE_API')
DATETIME_FORMAT = '%Y-%m-%d'


# archive_provisioning_bills
class Command(BaseCommand):
    help = 'Archive older provisioning bills'

    def handle(self, *args, **options):

        now = timezone.now()
        bills = ProvisioningBill.objects.filter(status='PAID',
                                                paid_at__gte=now - relativedelta(months=1),
                                                archived_at__isnull=True)

        for bill in bills:
            archive_provisioning_bill.delay(bill.id)
