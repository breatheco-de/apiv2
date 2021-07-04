from django.core.management.base import BaseCommand, CommandError
from ...actions import sync_tags, sync_automations


class Command(BaseCommand):
    help = 'Sync breathecode with active campaign'

    def handle(self, *args, **options):

        # sync_tags()
        self.stdout.write(self.style.SUCCESS("Successfully sync tags"))
