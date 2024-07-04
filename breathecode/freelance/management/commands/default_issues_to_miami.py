from django.core.management.base import BaseCommand
from breathecode.admissions.models import Academy
from ...models import Issue


class Command(BaseCommand):
    help = "Make all issues be from miami"

    def handle(self, *args, **options):

        academy = Academy.objects.filter(slug="downtown-miami").first()
        Issue.objects.filter(academy__isnull=True).update(academy=academy)

        self.stdout.write(self.style.SUCCESS("Successfully sync issues"))
