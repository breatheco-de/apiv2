from django.core.management.base import BaseCommand, CommandError
from ...models import Issue, RepositoryWebhook


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):

        date_limit = timezone.make_aware(datetime.now() - timedelta(days=10))

        webhooks = RepositoryWebhook.objects.filter(started_at__lt=date_limit)
        count = webhooks.count()
        webhooks.delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {str(count)} RepositoryWebhook's"))
