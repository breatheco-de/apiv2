from django.core.management.base import BaseCommand, CommandError
from ...models import TaskManager
from django.utils import timezone
from datetime import datetime
from datetime import timedelta


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):

        date_limit = timezone.make_aware(datetime.now() - timedelta(days=10))

        webhooks = TaskManager.objects.filter(created_at__lt=date_limit - timedelta(days=2))
        count = webhooks.count()
        webhooks.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {str(count)} TaskManager's"))
