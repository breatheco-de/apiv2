import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from ...models import Asset
from breathecode.admissions.models import Academy
from ...tasks import async_pull_from_github
from slugify import slugify

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'This command changes every readme_url instance that look like this >>https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md and turned into one that looks like this >>https://github.com/breatheco-de/exercise-postcard/blob/main/README.md'

    def handle(self, *args, **options):

        readme = Asset.objects.filter(
            readme_url='https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md'
        ).update(readme_url='https://github.com/breatheco-de/exercise-postcard/blob/main/README.md')
