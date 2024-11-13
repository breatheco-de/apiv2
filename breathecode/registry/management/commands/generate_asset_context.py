import logging

from django.core.management.base import BaseCommand

from ...models import Asset

# from ...tasks import async_build_asset_context

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate asset context for all assets."

    def handle(self, *args, **options):
        print("Hello")

        assets = Asset.objects.filter(assetcontext__isnull=True)
        print(assets.count())
        for asset in assets:
            print(asset.title)
