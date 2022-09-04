from django.core.management.base import BaseCommand, CommandError
from breathecode.admissions.models import Academy
from ...models import Issue, RepositoryIssueWebhook


class Command(BaseCommand):
    help = 'Delete logs and other garbage'

    def handle(self, *args, **options):
        RepositoryIssueWebhook.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Successfully deleted RepositoryIssueWebhook's"))
