import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Organization
from ...tasks import persist_organization_events
from django.utils import timezone


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

    def events(self, options):
        now = timezone.now()
        orgs = Organization.objects.all()
        count = 0
        for org in orgs:
            if org.eventbrite_key is None or org.eventbrite_key == "" or org.eventbrite_id is None or org.eventbrite_id == "":
                org.sync_status = 'ERROR'
                org.sync_desc = "Missing eventbrite key or id"
                org.save()
                self.stdout.write(
                    self.style.ERROR(
                        f"Organization {str(org)} is missing evenbrite key or ID"
                    ))
            else:
                org.sync_status = 'PENDING'
                org.sync_desc = "Running sync_eventbrite command at " + str(
                    now)
                org.save()
                persist_organization_events.delay({"org_id": org.id})
                count = count + 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Enqueued {count} of {len(orgs)} for sync events"))
