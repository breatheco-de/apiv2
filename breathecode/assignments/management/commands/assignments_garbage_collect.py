from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from assignments.models import LearnPackWebhook


class Command(BaseCommand):
    help = "Clean data from marketing module"

    def handle(self, *args, **options):
        self.delete_old_webhooks()

    def delete_old_webhooks(self, batch_size=1000):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        while True:
            old_webhooks = LearnPackWebhook.objects.filter(created_at__lt=thirty_days_ago).exclude(
                status__in=["ERROR", "PENDING"]
            )[:batch_size]

            if not old_webhooks.exists():
                break

            old_webhooks.delete()
