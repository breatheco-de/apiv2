import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from ...models import Asset
from breathecode.admissions.models import Academy
from ...tasks import async_pull_from_github
from slugify import slugify
import re

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'This command changes every readme_url instance with this structure >>https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md and turns it in one with this structure >>https://github.com/breatheco-de/exercise-postcard/blob/main/README.md'

    def handle(self, *args, **options):

        assets = Asset.objects.all()
        for asset in assets:
            readme_urls = asset.readme_url
            regex = re.search('^https://raw.githubusercontent.com', readme_urls)
            if regex:
                link_split = readme_urls.split('/')
                new_link = 'https://github.com' + '/' + link_split[3] + '/' + link_split[
                    4] + '/' + 'blob/main/README.md'
                readme_urls = new_link
