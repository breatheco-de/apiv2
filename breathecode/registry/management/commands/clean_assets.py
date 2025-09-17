import logging
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from ...models import Asset
from ...tasks import async_regenerate_asset_readme

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean assets asynchronously with rate limiting (without pulling from GitHub)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all assets instead of just those that need cleaning",
        )
        parser.add_argument(
            "--asset-type",
            type=str,
            help="Filter assets by type (e.g., PROJECT, EXERCISE, LESSON, QUIZ, VIDEO)",
        )
        parser.add_argument(
            "--status",
            type=str,
            help="Filter assets by status (e.g., PUBLISHED, DRAFT, NOT_STARTED)",
        )
        parser.add_argument(
            "--lang",
            type=str,
            help="Filter assets by language (e.g., en, es, it)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="Delay between API calls in seconds (default: 2.0)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Number of assets to process in each batch (default: 10)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without actually processing",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force processing even if recently cleaned",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Starting asset cleaning process...")
        )

        # Build filters
        filters = self._build_filters(options)
        
        # Get assets to process
        assets = self._get_assets_to_process(filters, options)
        
        if not assets.exists():
            self.stdout.write(
                self.style.WARNING("No assets found matching the criteria.")
            )
            return

        self.stdout.write(
            f"Found {assets.count()} assets to clean"
        )

        if options["dry_run"]:
            self._show_dry_run(assets)
            return

        # Process assets with throttling
        self._process_assets(assets, options)

        self.stdout.write(
            self.style.SUCCESS("Asset cleaning process completed!")
        )

    def _build_filters(self, options):
        """Build database filters based on command options."""
        filters = {}

        if options["asset_type"]:
            filters["asset_type"] = options["asset_type"]

        if options["status"]:
            filters["status"] = options["status"]

        if options["lang"]:
            filters["lang"] = options["lang"]

        # Only process assets that have readme content
        filters["readme__isnull"] = False
        filters["readme__gt"] = ""

        return filters

    def _get_assets_to_process(self, filters, options):
        """Get assets that need cleaning based on filters and options."""
        assets = Asset.objects.filter(**filters)

        if not options["all"] and not options["force"]:
            # Only process assets that haven't been cleaned recently
            # or have never been cleaned
            cutoff_time = timezone.now() - timedelta(hours=24)
            assets = assets.filter(
                Q(last_cleaning_at__isnull=True) | Q(last_cleaning_at__lt=cutoff_time)
            )

        # Order by last cleaning time (oldest first) and then by ID
        assets = assets.order_by("last_cleaning_at", "id")

        return assets

    def _show_dry_run(self, assets):
        """Show what would be processed in dry-run mode."""
        self.stdout.write(
            self.style.WARNING("DRY RUN MODE - No actual processing will occur")
        )
        
        for asset in assets[:20]:  # Show first 20
            last_clean = asset.last_cleaning_at or "Never"
            self.stdout.write(
                f"  - {asset.slug} ({asset.asset_type}) - Last clean: {last_clean}"
            )
        
        if assets.count() > 20:
            self.stdout.write(f"  ... and {assets.count() - 20} more assets")

    def _process_assets(self, assets, options):
        """Process assets with throttling and batching."""
        delay = options["delay"]
        batch_size = options["batch_size"]
        
        total_assets = assets.count()
        processed = 0
        
        self.stdout.write(
            f"Cleaning {total_assets} assets with {delay}s delay between calls..."
        )

        for i in range(0, total_assets, batch_size):
            batch = assets[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_assets + batch_size - 1) // batch_size
            
            self.stdout.write(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} assets)..."
            )

            for asset in batch:
                try:
                    self._process_single_asset(asset, options)
                    processed += 1
                    
                    # Show progress
                    if processed % 5 == 0 or processed == total_assets:
                        self.stdout.write(
                            f"  Progress: {processed}/{total_assets} assets processed"
                        )
                    
                    # Throttle between API calls
                    if processed < total_assets:  # Don't sleep after the last one
                        time.sleep(delay)
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing asset {asset.slug}: {str(e)}"
                        )
                    )
                    logger.exception(f"Error processing asset {asset.slug}")

            # Small delay between batches
            if i + batch_size < total_assets:
                self.stdout.write(f"  Waiting {delay * 2}s before next batch...")
                time.sleep(delay * 2)

    def _process_single_asset(self, asset, options):
        """Process a single asset by cleaning it."""
        self.stdout.write(f"  Cleaning {asset.slug}...")
        
        try:
            # Clean the asset
            self.stdout.write(f"    Queuing for cleaning...")
            async_regenerate_asset_readme.delay(asset.slug)
            
            self.stdout.write(
                self.style.SUCCESS(f"    ✓ {asset.slug} queued for cleaning")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"    ✗ Error processing {asset.slug}: {str(e)}")
            )
            raise
