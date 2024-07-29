from django.core.management.base import BaseCommand
from ...models import Issue


class Command(BaseCommand):
    help = "Sync breathecode with active campaign"

    def handle(self, *args, **options):

        Issue.objects.filter(status__in=["DOING", "IGNORED", "DRAFT", "TODO", "DOING"]).delete()

        self.stdout.write(self.style.SUCCESS("Successfully sync tags"))
