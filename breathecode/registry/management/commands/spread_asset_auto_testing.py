import logging
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.registry.models import Asset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Spread asset automatic testing over 30 days to prevent all assets from being tested on the same day"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the assets that would be updated without actually updating them",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Update all assets regardless of their current last_test_at value",
        )

    def handle(self, *args, **options):
        # Get all assets
        if options["force_all"]:
            assets = Asset.objects.all()
            self.stdout.write(
                self.style.WARNING("Force mode: updating ALL assets regardless of current last_test_at value")
            )
        else:
            # Only update assets that don't have last_test_at set, or have it set to the same recent value
            # indicating they might all be clustered on the same day
            recent_cutoff = timezone.now() - timedelta(days=7)
            assets = Asset.objects.filter(Q(last_test_at__isnull=True) | Q(last_test_at__gte=recent_cutoff))

        total_assets = assets.count()
        self.stdout.write(self.style.SUCCESS(f"Found {total_assets} assets to spread over 30 days"))

        if total_assets == 0:
            self.stdout.write(self.style.SUCCESS("No assets need updating. All done!"))
            return

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run - no assets will be updated"))

            # Show what would be done
            now = timezone.now()
            for i, asset in enumerate(assets[:10]):  # Show first 10 as example
                # Spread over 30 days, but going backwards from now so testing starts immediately
                days_ago = random.randint(0, 29)
                new_date = now - timedelta(days=days_ago)
                self.stdout.write(
                    f"{i}->  {asset.slug}: would set last_test_at to {new_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            if total_assets > 10:
                self.stdout.write(f"  ... and {total_assets - 10} more assets")
            return

        # Update assets with random last_test_at dates spread over the last 30 days
        updated = 0
        errors = 0
        now = timezone.now()

        # Create a list of all assets and shuffle it to ensure random distribution
        assets_list = list(assets)
        random.shuffle(assets_list)

        for asset in assets_list:
            try:
                # Spread over 30 days, but going backwards from now so testing starts immediately
                # Random distribution ensures even spread
                days_ago = random.randint(0, 29)
                new_date = now - timedelta(days=days_ago)

                old_date = asset.last_test_at
                asset.last_test_at = new_date
                asset.save(update_fields=["last_test_at"])

                self.stdout.write(
                    f"Updated {asset.slug}: {old_date or 'None'} -> {new_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                updated += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating asset {asset.slug}: {str(e)}"))
                errors += 1
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished spreading asset testing dates:\n"
                f"- Total assets processed: {total_assets}\n"
                f"- Successfully updated: {updated}\n"
                f"- Errors: {errors}\n"
                f"- Assets last_test_at is now spread over 30 days\n"
                f"- Testing will resume immediately with the new schedule"
            )
        )
