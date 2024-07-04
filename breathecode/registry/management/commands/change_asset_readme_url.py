import logging
from django.core.management.base import BaseCommand
from ...models import Asset
import re

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "This command changes every readme_url instance with this structure >>https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md and turns it in one with this structure >>https://github.com/breatheco-de/exercise-postcard/blob/main/README.md"

    def handle(self, *args, **options):

        assets = Asset.objects.filter(readme_url__startswith="https://raw.githubusercontent.com/")
        for asset in assets:
            result = re.findall(
                "^https?://raw.githubusercontent.com/([a-zA-Z-_0-9]+)/([a-zA-Z-_0-9]+)/(.+)$", asset.readme_url
            )

            if result:
                new = f"https://github.com/{result[0][0]}/{result[0][1]}/blob/{result[0][2]}"
                asset.readme_url = new
                asset.save()
