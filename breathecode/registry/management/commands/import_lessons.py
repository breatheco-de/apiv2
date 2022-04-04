import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from ...actions import create_asset
from ...models import AssetAlias
from ...tasks import async_sync_with_github
from slugify import slugify

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync exercises and projects from old breathecode'

    def handle(self, *args, **options):
        response = requests.get(f'https://content.breatheco.de/static/api/lessons.json')
        items = response.json()
        items.sort(key=lambda x: x['lang'] == 'es')
        count = 0
        for lesson in items:
            BASE_PATH = 'https://github.com/breatheco-de/content/blob/master/src/content/lesson/'
            lesson['repository'] = BASE_PATH + lesson['fileName']
            lesson['readme'] = BASE_PATH + lesson['fileName']

            if 'authors' in lesson and lesson['authors'] is not None:
                lesson['authors_username'] = ','.join(lesson['authors'])

            lesson['slug'] = lesson['fileName'].replace('.md', '')

            a, created = create_asset(lesson, asset_type='LESSON', force=True)

    def _exists(self, slug):
        aa = AssetAlias.objects.filter(Q(slug=slug) | Q(asset__slug=slug)).first()
        return aa is not None
