from django.core.management.base import BaseCommand
from ...models import ActiveCampaignAcademy, Tag, Automation


class Command(BaseCommand):
    help = "Sync breathecode with active campaign"

    def handle(self, *args, **options):

        academy = ActiveCampaignAcademy.objects.filter(academy__slug="downtown-miami").first()
        if academy is not None:
            Tag.objects.update(ac_academy=academy)
            Automation.objects.update(ac_academy=academy)
            self.stdout.write(self.style.SUCCESS("Successfully sync tags and academies"))
        else:
            self.stdout.write(self.style.ERROR("AC Academy not found"))
