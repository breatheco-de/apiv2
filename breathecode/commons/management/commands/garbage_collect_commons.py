from django.core.management.base import BaseCommand, CommandError
from ...models import TaskManager
from datetime import datetime
from datetime import timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):
        date_limit = timezone.now() - timedelta(days=2)

        webhooks = TaskManager.objects.filter(created_at__lt=date_limit)
        count = webhooks.count()
        webhooks.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {str(count)} TaskManager's"))
