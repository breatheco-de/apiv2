from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.marketing.tasks import async_activecampaign_webhook

from ...models import ActiveCampaignWebhook


class Command(BaseCommand):
    help = "Clean data from marketing module"

    def handle(self, *args, **options):

        hooks = ActiveCampaignWebhook.objects.filter(
            Q(run_at=None) | Q(run_at__lte=timezone.now() - timedelta(days=3)), status="PENDING"
        ).only("id")

        for h in hooks:
            async_activecampaign_webhook.delay(h.id)
