from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from breathecode.assignments.models import LearnPackWebhook


class Command(BaseCommand):
    help = "Clean old data from assignments module (webhooks and expired flags)"

    def handle(self, *args, **options):
        self.delete_old_webhooks()
        self.delete_expired_flags()

    def delete_old_webhooks(self, batch_size=5000, max_total=50000, days_old=5):
        cutoff = timezone.now() - timedelta(days=days_old)
        total_deleted = 0
        self.stdout.write(self.style.NOTICE("Starting garbage collection of old webhooks..."))

        while total_deleted < max_total:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    DELETE FROM assignments_learnpackwebhook
                    WHERE id IN (
                        SELECT id FROM assignments_learnpackwebhook
                        WHERE created_at < %s
                        ORDER BY created_at ASC
                        LIMIT %s
                    )
                """, [cutoff, batch_size])
                deleted = cursor.rowcount

            if deleted == 0:
                break

            total_deleted += deleted
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old webhooks."))

        self.stdout.write(
            self.style.SUCCESS(f"Garbage collection for assignments completed. Deleted {total_deleted} webhooks.")
        )

    def delete_expired_flags(self, batch_size=1000):
        try:
            from breathecode.registry.models import AssetFlag
        except ImportError:
            self.stdout.write(self.style.WARNING("AssetFlag model not available, skipping expired flag cleanup."))
            return

        now = timezone.now()
        total_deleted = 0
        self.stdout.write(self.style.NOTICE("Starting garbage collection of expired flags..."))

        while True:
            ids_to_delete = list(
                AssetFlag.objects
                .filter(expires_at__lt=now, status__in=["ACTIVE", "REVOKED"])
                .values_list("id", flat=True)[:batch_size]
            )

            if not ids_to_delete:
                break

            deleted, _ = AssetFlag.objects.filter(id__in=ids_to_delete).delete()
            total_deleted += deleted
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired flags."))

        self.stdout.write(
            self.style.SUCCESS(f"Expired flag cleanup completed. Deleted {total_deleted} expired flags.")
        )
