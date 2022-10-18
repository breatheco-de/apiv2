import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from ...actions import create_asset
from ...models import AssetAlias
from slugify import slugify
from breathecode.assessment.models import Assessment

logger = logging.getLogger(__name__)

HOST_ASSETS = 'https://assets.breatheco.de/apis'


class Command(BaseCommand):
    help = 'Sync exercises and projects from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)
        parser.add_argument(
            '--override',
            action='store_true',
            help='Delete and add again',
        )
        parser.add_argument('--limit',
                            action='store',
                            dest='limit',
                            type=int,
                            default=0,
                            help='How many to import')

    def handle(self, *args, **options):
        try:
            func = getattr(self, options['entity'], 'entity_not_found')
            func(options)
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')

    def _exists(self, slug):
        return AssetAlias.objects.filter(Q(slug=slug) | Q(asset__slug=slug)).first()

    def exercises(self, options):
        response = requests.get(f'{HOST_ASSETS}/registry/all', timeout=2)
        items = response.json()
        for slug in items:
            if self._exists(slug) and options['override'] == False:
                print('Skipping: Asset exercise with this alias ' + slug + ' already exists, use the')
                continue
            data = items[slug]
            if 'grading' in data:
                data['graded'] = data['grading']

            if 'tags' not in data:
                data['tags'] = []

            if 'language' in data:
                data['tags'].append(data.pop('language'))
            elif 'lang' in data:
                data['tags'].append(data.pop('language'))

            data['language'] = 'en'

            create_asset(data, asset_type='EXERCISE', force=(options['override'] == True))

    def projects(self, options):
        response = requests.get(f'{HOST_ASSETS}/project/registry/all', timeout=2)
        items = response.json()
        for slug in items:
            if self._exists(slug):
                print('Skipping: Asset project with this alias ' + slug + ' already exists')
                continue
            data = items[slug]
            if 'language' in data:
                lang = data.pop('language', False)
                if 'technologies' in data:
                    if lang not in data['technologies'] and lang:
                        data['technologies'].append(lang)
                elif lang:
                    data['technologies'] = [lang]

            data['language'] = 'en'

            create_asset(data, asset_type='PROJECT')

    def quiz(self, options):
        response = requests.get(f'{HOST_ASSETS}/quiz/all', timeout=2)
        items = response.json()
        items.sort(key=lambda x: x['info']['lang'] == 'es')
        for quiz in items:
            quiz['info']['slug'] = slugify(quiz['info']['slug']).lower()
            slug = quiz['info']['slug']

            if slug == 'new':
                print(f'Skipping quiz slug {slug}')
                continue

            lang = quiz['info']['lang']
            a = self._exists(slug)
            if a is not None:
                if lang not in ['en', 'us'] and a.slug == slug:
                    print(f'Fixing slug to {slug}.{lang} because {a.slug} == {slug}')
                    quiz['info']['translations'] = [lang, a.asset.lang]
                    slug += '.' + lang
                    quiz['info']['slug'] = slug

                if self._exists(slug) is not None:
                    print('Skipping: Asset quiz with this alias ' + slug + ' in ' + lang + ' already exists')
                    continue
                else:
                    print('Added lang to quiz slug: ' + slug)

            else:
                quiz['info']['translations'] = [lang]

            data = {
                'slug': quiz['info']['slug'],
                'title': quiz['info']['name'],
                'status': quiz['info']['status'].upper() if 'status' in quiz['info'] else 'DRAFT',
                'description': quiz['info']['main'],
                'lang': quiz['info']['lang'],
                'translations': quiz['info']['translations'],
                'config': quiz,
                'external': True,
                'interactive': True,
                'with_solutions': True,
                'graded': True,
            }
            create_asset(data, asset_type='QUIZ')
