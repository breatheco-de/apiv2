import os, requests, sys, pytz
from django.core.management.base import BaseCommand, CommandError
from ...models import Application
from ...tasks import monitor_app

class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

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

    def apps(self, options):

        apps = Application.objects.all()
        count = 0
        for a in apps:
            count += 1
            monitor_app.delay(a.id)
        
        self.stdout.write(self.style.SUCCESS(f"Enqueued {count} apps for diagnostic"))