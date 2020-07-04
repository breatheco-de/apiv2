import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Task, User
from ...actions import sync_student_tasks

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT="%Y-%m-%d"
class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)
        parser.add_argument(
            '--cohorts',
            type=str,
            default=None,
            help='Cohorts slugs to sync',
        )
        parser.add_argument(
            '--students',
            type=str,
            default=None,
            help='Cohorts slugs to sync',
        )

    def handle(self, *args, **options):
        try:
            func = getattr(self,options['entity'],'entity_not_found') 
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def tasks(self, options):

        if options['students'] is not None:
            emails = options['students'].split(",")
            for email in emails:
                user = User.objects.filter(email=email).first()
                if user is None:
                    raise CommandError(f"Student {email} not found new API")

                sync_student_tasks(user)