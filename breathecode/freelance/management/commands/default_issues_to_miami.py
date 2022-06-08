from django.core.management.base import BaseCommand, CommandError
from ...actions import sync_tags, sync_automations
from ...models import Issue


class Command(BaseCommand):
    help = 'Make all issues be from miami'

    def handle(self, *args, **options):

        academy = Academy.objects.filter(slug='downtown-miami').first()
        Issue.objects.filter(academy__isnull=True).update(academy=academy)

        self.stdout.write(self.style.SUCCESS('Successfully sync issues'))
