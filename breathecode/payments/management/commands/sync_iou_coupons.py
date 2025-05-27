import logging

from django.core.management.base import BaseCommand

from breathecode.payments.models import PlanFinancing, Subscription

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Migration tool to sync existing coupons from invoice bags to Subscriptions and PlanFinancings. "
        "NOTE: New subscriptions and plan financings automatically include coupons during creation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--subscription-id",
            type=int,
            dest="subscription_id",
            help="Specific subscription ID to process",
        )
        parser.add_argument(
            "--plan-financing-id",
            type=int,
            dest="plan_financing_id",
            help="Specific plan financing ID to process",
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
            default=1000,
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Display more detailed output",
            default=False,
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            dest="active_only",
            help="Process only active records",
            default=False,
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        subscription_id = options.get("subscription_id")
        plan_financing_id = options.get("plan_financing_id")
        batch_size = options["batch_size"]
        verbose = options["verbose"]
        active_only = options["active_only"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode, no changes will be made"))

        if verbose:
            self.stdout.write(f"Batch size: {batch_size}")
            self.stdout.write(f"Active only: {active_only}")

        # Process subscriptions
        self.stdout.write("Processing subscriptions...")
        subscriptions = Subscription.objects.all()

        if subscription_id:
            subscriptions = subscriptions.filter(id=subscription_id)

        if active_only:
            subscriptions = subscriptions.filter(status="ACTIVE")

        total_count = subscriptions.count()
        if verbose:
            self.stdout.write(f"Found {total_count} subscriptions to process")

        success_count = 0
        error_count = 0
        skipped_count = 0

        # Process in batches to avoid memory issues
        for i in range(0, total_count, batch_size):
            if verbose:
                self.stdout.write(f"Processing batch {i//batch_size + 1} ({i} to {min(i+batch_size, total_count)})")

            batch = subscriptions[i : i + batch_size]

            for subscription in batch:
                try:
                    # Get the first invoice for this subscription
                    first_invoice = subscription.invoices.order_by("created_at").first()

                    if not first_invoice:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"Subscription {subscription.id}: No invoices found, skipping")
                        continue

                    if not first_invoice.bag:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(
                                f"Subscription {subscription.id}: No bag found for invoice {first_invoice.id}, skipping"
                            )
                        continue

                    bag = first_invoice.bag
                    coupons = bag.coupons.all()

                    if not coupons.exists():
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(
                                f"Subscription {subscription.id}: No coupons found for bag {bag.id}, skipping"
                            )
                        continue

                    current_coupons = subscription.coupons.all()
                    new_coupons = [c for c in coupons if c not in current_coupons]

                    if new_coupons:
                        coupon_ids = [c.id for c in new_coupons]
                        coupon_slugs = [c.slug for c in new_coupons]

                        self.stdout.write(f"Subscription {subscription.id}: Adding coupons {coupon_slugs}")

                        if not dry_run:
                            subscription.coupons.add(*coupon_ids)
                            success_count += 1
                        else:
                            success_count += 1
                    else:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"Subscription {subscription.id}: No new coupons to add, skipping")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing subscription {subscription.id}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f"Error processing subscription {subscription.id}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {total_count} subscriptions: {success_count} updated, {skipped_count} skipped, {error_count} errors"
            )
        )

        # Process plan financings
        self.stdout.write("Processing plan financings...")
        financings = PlanFinancing.objects.all()

        if plan_financing_id:
            financings = financings.filter(id=plan_financing_id)

        if active_only:
            financings = financings.filter(status="ACTIVE")

        total_count = financings.count()
        if verbose:
            self.stdout.write(f"Found {total_count} plan financings to process")

        success_count = 0
        error_count = 0
        skipped_count = 0

        # Process in batches to avoid memory issues
        for i in range(0, total_count, batch_size):
            if verbose:
                self.stdout.write(f"Processing batch {i//batch_size + 1} ({i} to {min(i+batch_size, total_count)})")

            batch = financings[i : i + batch_size]

            for financing in batch:
                try:
                    # Get the first invoice for this financing
                    first_invoice = financing.invoices.order_by("created_at").first()

                    if not first_invoice:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"PlanFinancing {financing.id}: No invoices found, skipping")
                        continue

                    if not first_invoice.bag:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(
                                f"PlanFinancing {financing.id}: No bag found for invoice {first_invoice.id}, skipping"
                            )
                        continue

                    bag = first_invoice.bag
                    coupons = bag.coupons.all()

                    if not coupons.exists():
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(
                                f"PlanFinancing {financing.id}: No coupons found for bag {bag.id}, skipping"
                            )
                        continue

                    current_coupons = financing.coupons.all()
                    new_coupons = [c for c in coupons if c not in current_coupons]

                    if new_coupons:
                        coupon_ids = [c.id for c in new_coupons]
                        coupon_slugs = [c.slug for c in new_coupons]

                        self.stdout.write(f"PlanFinancing {financing.id}: Adding coupons {coupon_slugs}")

                        if not dry_run:
                            financing.coupons.add(*coupon_ids)
                            success_count += 1
                        else:
                            success_count += 1
                    else:
                        skipped_count += 1
                        if verbose:
                            self.stdout.write(f"PlanFinancing {financing.id}: No new coupons to add, skipping")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing financing {financing.id}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f"Error processing financing {financing.id}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {total_count} financings: {success_count} updated, {skipped_count} skipped, {error_count} errors"
            )
        )
