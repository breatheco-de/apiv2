import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.authenticate import tasks
from breathecode.authenticate.models import FirstPartyWebhookLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage first party webhooks'

    def route(self, webhook: FirstPartyWebhookLog):
        if webhook.type == 'user.created' or webhook.type == 'user.updated':
            return tasks.import_external_user.delay(webhook.id)

        webhook.status = 'ERROR'
        webhook.status_text = 'Invalid webhook type'
        webhook.save()

    def handle(self, *args, **options):
        now = timezone.now()

        newest = FirstPartyWebhookLog.objects.filter(attempts=0, status='PENDING',
                                                     external_id__isnull=False).only('id', 'type')
        retries = FirstPartyWebhookLog.objects.filter(
            updated_at__lte=now - timedelta(minutes=20), status='PENDING',
            external_id__isnull=False).exclude(Q(attempts__gt=5) | Q(attempts=0)).only('id', 'type')

        for retry in retries:
            self.route(retry)

        for new in newest:
            self.route(new)
