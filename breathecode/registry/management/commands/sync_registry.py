import os, requests, logging
from django.core.management.base import BaseCommand, CommandError
from ...actions import create_asset

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
        parser.add_argument(
              '--limit',
               action='store',
               dest='limit',
               type=int,
               default=0,
               help='How many to import'
        )

    def handle(self, *args, **options):
        try:
            func = getattr(self,options['entity'],'entity_not_found') 
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def exercises(self, *args, **options):
        response = requests.get(f"{HOST_ASSETS}/registry/all")
        items = response.json()
        for slug in items:
            data = items[slug]
            create_asset(data)


    def projects(self, *args, **options):
        response = requests.get(f"{HOST_ASSETS}/project/registry/all")
        items = response.json()
        for slug in items:
            data = items[slug]
            create_asset(data)
