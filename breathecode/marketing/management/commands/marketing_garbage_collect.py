from django.core.management.base import BaseCommand
from django.db import connection

from breathecode.marketing.models import EmailDomainValidation


class Command(BaseCommand):
    help = "Clean data from marketing module"

    def handle(self, *args, **options):
        self.delete_old_webhooks()
        self.clean_expired_email_validations()

    def delete_old_webhooks(self):
        cursor = connection.cursor()
        # status = 'ERROR' or status = 'PENDING' AND
        cursor.execute("DELETE FROM marketing_activecampaignwebhook WHERE created_at < NOW() - INTERVAL '30 days'")

        cursor.execute("DELETE FROM marketing_activecampaignwebhook WHERE status <> 'ERROR' AND status <> 'PENDING'")

    def clean_expired_email_validations(self):
        """Limpia registros de validación de emails expirados"""
        deleted_count = EmailDomainValidation.clean_expired()
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Cleaned {deleted_count} expired email validation records")
            )
