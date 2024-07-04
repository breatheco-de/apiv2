import os

from django.core.management.base import BaseCommand

from breathecode.assessment.models import UserAssessment

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Close user assessments and totalize scores"

    def handle(self, *args, **options):

        unfinished_ua = UserAssessment.objects.filter(finished_at__isnull=True, status="SENT")
        total = unfinished_ua.count()
        unfinished_ua.update(status="ERROR", status_text="Unfinished user assessment")
        self.stdout.write(self.style.SUCCESS(f"{total} user assessments automatically closed with error"))
