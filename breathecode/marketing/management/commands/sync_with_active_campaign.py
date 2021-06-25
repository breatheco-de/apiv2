from django.core.management.base import BaseCommand, CommandError
from ...actions import sync_tags, sync_automations
from ...models import ActiveCampaignAcademy


class Command(BaseCommand):
    help = 'Sync breathecode with active campaign'

    def handle(self, *args, **options):

        academies = ActiveCampaignAcademy.objects.all()
        for a in academies:
            sync_tags(a)
            self.stdout.write(self.style.SUCCESS("Successfully sync tags"))

            sync_automations(a)
            self.stdout.write(
                self.style.SUCCESS("Successfully sync automations"))
