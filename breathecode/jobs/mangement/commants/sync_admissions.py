import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Academy, SpecialtyMode, Cohort, User, CohortUser, Syllabus
from breathecode.authenticate.models import Profile

HOST_ASSETS = 'https://assets.breatheco.de/apis'
API_URL = os.getenv('API_URL', '')
HOST_ASSETS = 'https://assets.breatheco.de/apis'
HOST = os.environ.get('OLD_BREATHECODE_API')
DATETIME_FORMAT = '%Y-%m-%d'


class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

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
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def academies(self, options):

        response = requests.get(f'{HOST}/locations/')
        locations = response.json()

        for loc in locations['data']:
            aca = Academy.objects.filter(slug=loc['slug']).first()
            if aca is None:
                a = Academy(
                    slug=loc['slug'],
                    active_campaign_slug=loc['slug'],
                    name=loc['name'],
                    street_address=loc['address'],
                )
                a.save()
                self.stdout.write(self.style.SUCCESS(f'Academy {a.slug} added'))
            else:
                self.stdout.write(self.style.NOTICE(f'Academy {aca.slug} skipped'))
