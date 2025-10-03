import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from breathecode.payments.models import Coupon

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remove all plans from coupons with referral type different from NO_REFERRAL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--coupon-id",
            type=int,
            dest="coupon_id",
            help="Specific coupon ID to process",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Run without making changes",
            default=False,
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            dest="batch_size",
            help="Process records in batches of this size",
            default=100,
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Display more detailed output",
            default=False,
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.batch_size = options["batch_size"]
        self.verbose = options["verbose"]

        coupons = self.get_coupons_to_process(options["coupon_id"])
        if not coupons.exists():
            self.stdout.write(self.style.WARNING("No coupons found matching the criteria"))
            return
        self.stdout.write(f"Found {coupons.count()} coupons to process")

        total_processed = 0
        total_updated = 0
        total_errors = 0
        for i in range(0, coupons.count(), self.batch_size):
            batch = coupons[i : i + self.batch_size]
            try:
                with transaction.atomic():
                    batch_updated = self.process_coupon_batch(batch)
                    total_updated += batch_updated
                    total_processed += len(batch)
                    if self.verbose:
                        self.stdout.write(
                            f"Processed batch {i//self.batch_size + 1}: {len(batch)} coupons, {batch_updated} updated"
                        )
            except Exception as e:
                total_errors += len(batch)
                logger.error(f"Error processing batch {i//self.batch_size + 1}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error processing batch {i//self.batch_size + 1}: {str(e)}"))
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Processing complete: {total_processed} processed, {total_updated} updated, {total_errors} errors"
            )
        )

    def get_coupons_to_process(self, coupon_id):
        """Get coupons with referral type different from NO_REFERRAL"""
        if coupon_id:
            return Coupon.objects.filter(id=coupon_id).exclude(referral_type=Coupon.Referral.NO_REFERRAL)
        else:
            return Coupon.objects.exclude(referral_type=Coupon.Referral.NO_REFERRAL)

    def process_coupon_batch(self, coupons) -> int:
        """Process a batch of coupons - remove all plans"""
        updated_count = 0
        for coupon in coupons:
            try:
                original_plans = list(coupon.plans.values_list("slug", flat=True))
                if self.verbose:
                    self.stdout.write(f"Processing coupon {coupon.id} ({coupon.slug}): {original_plans}")
                # Check if coupon has plans to remove
                if not original_plans:
                    if self.verbose:
                        self.stdout.write(f"  No plans to remove for coupon {coupon.id}")
                    continue
                if not self.dry_run:
                    # Remove all plans
                    coupon.plans.clear()
                    coupon.save()
                updated_count += 1
                if self.verbose:
                    self.stdout.write(f"  Removed all plans from coupon {coupon.id}: {original_plans} -> []")
            except Exception as e:
                logger.error(f"Error processing coupon {coupon.id}: {str(e)}")
                if self.verbose:
                    self.stdout.write(f"  Error processing coupon {coupon.id}: {str(e)}")
                raise
        return updated_count
