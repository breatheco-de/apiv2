from django.core.management.base import BaseCommand
from ...models import RepositoryWebhook
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Delete logs and other garbage"

    def handle(self, *args, **options):

        date_limit = timezone.make_aware(timezone.now() - timedelta(days=10))

        RepositoryWebhook.objects.filter(run_at__isnull=True).delete()

        webhooks = RepositoryWebhook.objects.filter(run_at__lt=date_limit)
        count = webhooks.count()
        webhooks.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {str(count)} RepositoryWebhook's"))
