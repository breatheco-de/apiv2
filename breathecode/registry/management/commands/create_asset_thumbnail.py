import os
from django.core.management.base import BaseCommand
from django.db.models import Q
from ...tasks import async_create_asset_thumbnail
from ...models import Asset


class Command(BaseCommand):
    help = 'Generate preview for assets without preview'

    def handle(self, *args, **options):

        DEFAULT_ASSET_PREVIEW_URL = os.getenv('DEFAULT_ASSET_PREVIEW_URL', '')
        assets = Asset.objects.filter(Q(preview=None) | Q(preview=DEFAULT_ASSET_PREVIEW_URL))
        for a in assets:
            async_create_asset_thumbnail.delay(a.slug)
