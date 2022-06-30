from django.core.management.base import BaseCommand, CommandError
from breathecode.admissions.models import Academy
from ...models import EventbriteWebhook


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):
        EventbriteWebhook.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Successfully deleted EventbriteWebhook's"))
