import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Assessment, Question, Option
from ...actions import create_from_json

HOST_ASSETS = 'https://assets.breatheco.de/apis'
API_URL = os.getenv('API_URL', '')
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

    def quiz(self, options):

        response = requests.get(f'{HOST_ASSETS}/quiz/all', timeout=2)
        quizzes = response.json()

        for quiz in quizzes:
            a = create_from_json(payload=quiz)
            self.stdout.write(self.style.SUCCESS(f"Creating assesment {quiz['info']['slug']}"))
