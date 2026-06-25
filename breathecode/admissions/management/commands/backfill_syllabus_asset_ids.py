from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.admissions.actions import enrich_syllabus_asset_ids
from breathecode.admissions.models import SyllabusVersion


class Command(BaseCommand):
    help = "Backfill registry asset ids into syllabus version JSON payloads"

    def add_arguments(self, parser):
        parser.add_argument("--syllabus-slug", type=str, default=None, help="Only process this syllabus slug")
        parser.add_argument("--version", type=int, default=None, help="Only process this syllabus version number")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many versions would change without writing to the database",
        )

    def handle(self, *args, **options):
        queryset = SyllabusVersion.objects.all().order_by("id")

        if options["syllabus_slug"]:
            queryset = queryset.filter(syllabus__slug=options["syllabus_slug"])

        if options["version"] is not None:
            queryset = queryset.filter(version=options["version"])

        updated = 0
        scanned = 0

        for version in queryset.iterator():
            scanned += 1
            enriched = enrich_syllabus_asset_ids(version.json)
            if enriched == version.json:
                continue

            updated += 1
            if options["dry_run"]:
                continue

            SyllabusVersion.objects.filter(pk=version.pk).update(json=enriched, updated_at=timezone.now())

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(f"Scanned {scanned} syllabus version(s); {updated} would be updated")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Scanned {scanned} syllabus version(s); updated {updated}"))
