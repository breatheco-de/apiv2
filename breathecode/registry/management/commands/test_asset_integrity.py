import logging

from django.core.management.base import BaseCommand

from ...models import Asset
from ...tasks import async_test_asset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set published date to legacy articles"

    def handle(self, *args, **options):

        assets = Asset.objects.filter(status="PUBLISHED").exclude(asseterrorlog__status="ERROR").distinct()
        for a in assets:
            print(f"Testing asynchronusly {a.slug}")
            async_test_asset.delay(a.slug)
