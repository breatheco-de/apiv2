from django.core.management.base import BaseCommand
from ...models import Organization
from ...tasks import persist_organization_events
from django.utils import timezone


class Command(BaseCommand):
    help = "Sync from eventbrite, please make sure to add the argument, Eg: sync_eventbrite events"

    def add_arguments(self, parser):
        parser.add_argument("entity", type=str)
        parser.add_argument(
            "--override",
            action="store_true",
            help="Delete and add again",
        )
        parser.add_argument("--limit", action="store", dest="limit", type=int, default=0, help="How many to import")

    def handle(self, *args, **options):
        if "entity" not in options:
            return self.stderr.write(self.style.ERROR("Entity argument not provided"))

        try:
            func = getattr(self, options["entity"])
            func(options)
        except Exception:
            return self.stderr.write(self.style.ERROR(f'Sync method for `{options["entity"]}` no Found!'))

    def events(self, options):
        now = timezone.now()
        orgs = Organization.objects.all()
        count = 0
        for org in orgs:
            if not org.eventbrite_key or not org.eventbrite_id:
                org.sync_status = "ERROR"
                org.sync_desc = "Missing eventbrite key or id"
                org.save()
                self.stderr.write(self.style.ERROR(f"Organization {str(org)} is missing evenbrite key or ID"))
            else:
                org.sync_status = "PENDING"
                org.sync_desc = "Running sync_eventbrite command at " + str(now)
                org.save()
                persist_organization_events.delay({"org_id": org.id})
                count = count + 1

        self.stdout.write(self.style.SUCCESS(f"Enqueued {count} of {len(orgs)} for sync events"))
