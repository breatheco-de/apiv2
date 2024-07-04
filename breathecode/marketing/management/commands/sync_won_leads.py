from django.core.management.base import BaseCommand
from ...models import FormEntry
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Sync breathecode with active campaign"

    def handle(self, *args, **options):

        entries = FormEntry.objects.filter(deal_status="WON", user__isnull=True)
        for entry in entries:
            user = User.objects.filter(email=entry.email).first()
            if user is not None:
                entry.user = user
                entry.save()

                self.stdout.write(self.style.SUCCESS(f"Found user for formentry {entry.email}, updating..."))

        self.stdout.write(self.style.SUCCESS("Finished."))
