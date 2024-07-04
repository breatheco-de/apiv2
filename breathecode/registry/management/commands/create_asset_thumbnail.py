import os

from django.core.management.base import BaseCommand
from django.db.models import Q

from ...models import Asset
from ...tasks import async_create_asset_thumbnail


class Command(BaseCommand):
    help = "Generate preview for assets without preview"

    def handle(self, *args, **options):

        default_asset_preview_url = os.getenv("DEFAULT_ASSET_PREVIEW_URL", "")
        assets = Asset.objects.filter(Q(preview=None) | Q(preview=default_asset_preview_url))
        for a in assets:
            async_create_asset_thumbnail.delay(a.slug)
