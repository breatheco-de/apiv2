import logging
from django.core.management.base import BaseCommand
from ...models import Asset
from breathecode.admissions.models import Academy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Assign miami as default academy for lessons"

    def handle(self, *args, **options):

        miami = Academy.objects.filter(slug="downtown-miami").first()
        Asset.objects.filter(academy__isnull=True).update(academy=miami)
        Asset.objects.filter(status="OK").update(status="PUBLISHED")
        Asset.objects.filter(status="UNASSIGNED").update(status="NOT_STARTED")
