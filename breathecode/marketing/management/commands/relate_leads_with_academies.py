from django.core.management.base import BaseCommand
from ...models import FormEntry
from breathecode.admissions.models import Academy


class Command(BaseCommand):
    help = "Sync breathecode with active campaign"

    def handle(self, *args, **options):
        leads_without_academy = FormEntry.objects.filter(academy__isnull=True, location__isnull=False)
        counts = {"attempts": 0, "assigned": 0}

        for l in leads_without_academy:
            counts["attempts"] += 1
            print("Location: ", l.location)
            if l.location != "":
                academy = Academy.objects.filter(slug=l.location.strip()).first()
                if academy is not None:
                    l.academy = academy
                    l.location = l.location.strip()
                    l.save()
                    counts["assigned"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'{counts["attempts"]} leads were found without academy and {counts["assigned"]} were fixed'
            )
        )
