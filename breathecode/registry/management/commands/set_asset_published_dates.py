import logging
from django.core.management.base import BaseCommand
from ...models import Asset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set published date to legacy articles"

    def handle(self, *args, **options):

        assets = Asset.objects.filter(published_at__isnull=True, status="PUBLISHED", category__isnull=False)
        for a in assets:
            a.published_at = a.updated_at
            a.save()
