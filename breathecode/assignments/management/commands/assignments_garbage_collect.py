from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.assignments.models import LearnPackWebhook


class Command(BaseCommand):
    help = "Clean old data from assignments module (webhooks and expired flags)"

    def handle(self, *args, **options):
        self.delete_old_webhooks()
        self.delete_expired_flags()

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

    def delete_expired_flags(self, batch_size=1000):
        """Delete expired AssetFlags from the database."""
        try:
            from breathecode.registry.models import AssetFlag
        except ImportError:
            self.stdout.write(self.style.WARNING("AssetFlag model not available, skipping expired flag cleanup."))
            return

        now = timezone.now()
        self.stdout.write(self.style.NOTICE("Starting garbage collection of expired flags..."))

        total_deleted = 0
        while True:
            # Find expired flags (where expires_at is in the past and status is not already EXPIRED)
            expired_flags = AssetFlag.objects.filter(
                expires_at__lt=now, status__in=["ACTIVE", "REVOKED"]  # Don't re-process already EXPIRED flags
            )[:batch_size]

            if not expired_flags.exists():
                self.stdout.write(self.style.SUCCESS("No more expired flags to delete."))
                break

            count = expired_flags.count()
            ids_to_delete = list(expired_flags.values_list("id", flat=True))

            # Actually delete the expired flags for security
            AssetFlag.objects.filter(id__in=ids_to_delete).delete()

            self.stdout.write(self.style.SUCCESS(f"Deleted {count} expired flags."))
            total_deleted += count

        self.stdout.write(self.style.SUCCESS(f"Expired flag cleanup completed. Deleted {total_deleted} expired flags."))
