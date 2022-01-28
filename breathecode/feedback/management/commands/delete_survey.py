import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Survey

HOST = os.environ.get('OLD_BREATHECODE_API')
DATETIME_FORMAT = '%Y-%m-%d'


class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)

    def handle(self, *args, **options):
        try:
            func = getattr(self, options['entity'], 'entity_not_found')
        except TypeError:
            print(f'Delete method for {options["entity"]} no Found!')

        func(options)

    def all(self, options):
        Survey.objects.all().delete()
