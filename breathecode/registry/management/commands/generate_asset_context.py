import logging

from django.core.management.base import BaseCommand

from ...models import Asset, AssetContext
from ...tasks import async_build_asset_context

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate asset context for all assets."

    def handle(self, *args, **options):
        assets = Asset.objects.filter(assetcontext__isnull=True)
        for asset in assets:
            try:
                AssetContext.objects.update_or_create(asset=asset, defaults={"status": "PROCESSING"})
                async_build_asset_context.delay(asset.id)

            except Exception as e:
                AssetContext.objects.update_or_create(asset=asset, defaults={"status": "ERROR", "status_text": e})
