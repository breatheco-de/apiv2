import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from ...actions import create_asset
from ...models import Asset
from breathecode.admissions.models import Academy
from ...tasks import async_pull_from_github
from slugify import slugify

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Assign miami as default academy for lessons'

    def handle(self, *args, **options):

        miami = Academy.objects.filter(slug='downtown-miami').first()
        Asset.objects.filter(academy__isnull=True).update(academy=miami)
        Asset.objects.filter(status='OK').update(status='PUBLISHED')
        Asset.objects.filter(status='UNNASIGNED').update(status='UNASSIGNED')
