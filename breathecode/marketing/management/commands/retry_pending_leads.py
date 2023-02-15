from django.core.management.base import BaseCommand, CommandError
from ...tasks import persist_single_lead
from ...models import FormEntry
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Retry sending pending leads to active campaign'

    def handle(self, *args, **options):

        entries = FormEntry.objects.filter(storage_status='PENDING')
        for entry in entries:
            persist_single_lead.delay(entry.toFormData())
