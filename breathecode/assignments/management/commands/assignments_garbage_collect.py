from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.assignments.models import LearnPackWebhook


class Command(BaseCommand):
    help = "Clean data from marketing module"

    def handle(self, *args, **options):
        self.delete_old_webhooks()

    def delete_old_webhooks(self, batch_size=1000):
        five_days_ago = timezone.now() - timedelta(days=5)
        self.stdout.write(self.style.NOTICE("Starting garbage collection of old webhooks..."))

        total_deleted = 0
        while True:
            old_webhooks = LearnPackWebhook.objects.filter(created_at__lt=five_days_ago)[:batch_size]

            if not old_webhooks.exists():
                self.stdout.write(self.style.SUCCESS("No more old webhooks to delete."))
                break

            count = old_webhooks.count()
            ids_to_delete = list(old_webhooks.values_list("id", flat=True))
            LearnPackWebhook.objects.filter(id__in=ids_to_delete).delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} old webhooks."))
            total_deleted += count

        self.stdout.write(
            self.style.SUCCESS(f"Garbage collection for assignments completed. Deleted {total_deleted} webhooks.")
        )
