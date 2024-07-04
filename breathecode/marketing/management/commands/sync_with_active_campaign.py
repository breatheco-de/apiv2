from django.core.management.base import BaseCommand
from django.utils import timezone
from ...actions import sync_tags, sync_automations
from ...models import ActiveCampaignAcademy, ActiveCampaignWebhook


class Command(BaseCommand):
    help = "Sync breathecode with active campaign"

    def handle(self, *args, **options):

        academies = ActiveCampaignAcademy.objects.all()
        for a in academies:
            self.stdout.write(self.style.SUCCESS(f"Synching sync tags for {a.academy.name}"))
            sync_tags(a)

            sync_automations(a)
            self.stdout.write(self.style.SUCCESS("Synching automations"))

            # delete webhook history from 30 days ago
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            ActiveCampaignWebhook.objects.filter(ac_academy__id=a.id, run_at__lt=thirty_days_ago).delete()
            self.stdout.write(self.style.SUCCESS("Cleaning webhook log from more than 30 days ago"))
