from django.core.management.base import BaseCommand
from ...tasks import persist_single_lead
from ...models import FormEntry


class Command(BaseCommand):
    help = "Retry sending pending leads to active campaign"

    def handle(self, *args, **options):

        entries = FormEntry.objects.filter(storage_status="PENDING")
        for entry in entries:
            persist_single_lead.delay(entry.to_form_data())
