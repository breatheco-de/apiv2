import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from ...actions import create_asset, sync_with_github
from ...tasks import async_sync_with_github
from ...models import Asset

logger = logging.getLogger(__name__)

HOST_ASSETS = "https://assets.breatheco.de/apis"


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
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def projects(self, *args, **options):
        projects = Asset.objects.filter(asset_type='PROJECT')
        for p in projects:
            async_sync_with_github.delay(p.slug)
