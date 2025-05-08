import logging

from django.core.management.base import BaseCommand

from breathecode.registry.models import Asset
from breathecode.registry.tasks import sync_asset_telemetry_stats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync telemetry stats for all assets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the assets that would be processed without actually processing them",
        )

    def handle(self, *args, **options):
        assets = Asset.objects.all()
        total_assets = assets.count()

        self.stdout.write(self.style.SUCCESS(f"Found {total_assets} assets to process"))

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run - no assets will be processed"))
            return

        processed = 0
        errors = 0

        for asset in assets:
            try:
                self.stdout.write(f"Processing asset {asset.slug} ({asset.id})")
                sync_asset_telemetry_stats.delay(asset.id)
                processed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing asset {asset.slug}: {str(e)}"))
                errors += 1
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished processing assets:\n"
                f"- Total assets: {total_assets}\n"
                f"- Successfully queued: {processed}\n"
                f"- Errors: {errors}"
            )
        )
