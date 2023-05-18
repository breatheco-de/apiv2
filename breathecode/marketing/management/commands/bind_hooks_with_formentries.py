from django.core.management.base import BaseCommand, CommandError
from ...models import ActiveCampaignWebhook
from ...actions import bind_formentry_with_webhook
from django.contrib.auth.models import User
from django.db import connection


class Command(BaseCommand):
    help = 'Clean data from marketing module'

    def handle(self, *args, **options):

        hooks = ActiveCampaignWebhook.objects.filter(status='ERROR')
        for h in hooks:
            bind_formentry_with_webhook(h)
