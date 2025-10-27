from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from ...models import Consumable, ServiceStockScheduler


class Command(BaseCommand):
    help = "Backfill subscription and plan_financing fields for existing Consumable records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of consumables to process per batch (default: 100)",
        )
        parser.add_argument(
            "--include-expired",
            action="store_true",
            help="Include consumables with expired valid_until dates",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            dest="user_id",
            help="Only process consumables related to this user id",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        include_expired = options["include_expired"]
        utc_now = timezone.now()
        user_id = options.get("user_id")

        # Find all consumables without subscription or plan_financing set and with valid_until defined
        consumables_to_update = Consumable.objects.filter(
            subscription__isnull=True, plan_financing__isnull=True, valid_until__isnull=False
        )

        # By default, exclude expired consumables; include them only when --include-expired is passed
        if not include_expired:
            consumables_to_update = consumables_to_update.filter(valid_until__gte=utc_now)

        if user_id:
            consumables_to_update = consumables_to_update.filter(
                Q(user__id=user_id)
                | Q(subscription_seat__user__id=user_id)
                | Q(subscription_billing_team__seats__user__id=user_id)
            ).distinct()

        consumables_to_update = consumables_to_update.order_by("id")

        total_count = consumables_to_update.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No consumables need to be updated"))
            return

        self.stdout.write(f"Found {total_count} consumables to process")

        updated_count = 0
        skipped_count = 0
        error_count = 0
        expired_count = 0
        mismatch_count = 0
        not_in_list_count = 0
        would_update_ids = []
        updated_ids = []
        would_update_details = []
        updated_details = []

        # Process in batches
        for i in range(0, total_count, batch_size):
            batch = consumables_to_update[i : i + batch_size]

            for consumable in batch:
                try:
                    # Find schedulers that link to this consumable
                    schedulers = ServiceStockScheduler.objects.filter(consumables=consumable).select_related(
                        "subscription_handler__subscription",
                        "plan_handler__subscription",
                        "plan_handler__plan_financing",
                    )

                    if not schedulers.exists():
                        self.stdout.write(
                            self.style.WARNING(f"Consumable {consumable.id}: No scheduler found, skipping")
                        )
                        skipped_count += 1
                        continue

                    # Get the first scheduler (should typically only be one)
                    scheduler = schedulers.first()

                    # SAFETY CHECK 1: Verify consumable is in scheduler's consumables list
                    if not scheduler.consumables.filter(id=consumable.id).exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f"Consumable {consumable.id}: Not in scheduler {scheduler.id} consumables list, skipping"
                            )
                        )
                        not_in_list_count += 1
                        continue

                    # SAFETY CHECK 2: Verify valid_until matches between consumable and scheduler
                    if consumable.valid_until != scheduler.valid_until:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Consumable {consumable.id}: valid_until mismatch "
                                f"(consumable: {consumable.valid_until}, scheduler: {scheduler.valid_until}), skipping"
                            )
                        )
                        mismatch_count += 1
                        continue

                    # SAFETY CHECK 3: Verify valid_until is still valid (not expired)
                    if not include_expired:
                        if consumable.valid_until and consumable.valid_until < utc_now:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Consumable {consumable.id}: Expired (valid_until: {consumable.valid_until}), skipping"
                                )
                            )
                            expired_count += 1
                            continue

                    subscription = None
                    plan_financing = None

                    if scheduler.subscription_handler:
                        subscription = scheduler.subscription_handler.subscription
                        source = "subscription_handler"
                    elif scheduler.plan_handler:
                        subscription = scheduler.plan_handler.subscription
                        plan_financing = scheduler.plan_handler.plan_financing
                        source = "plan_handler"
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Consumable {consumable.id}: Scheduler {scheduler.id} has no handler, skipping"
                            )
                        )
                        skipped_count += 1
                        continue

                    if not subscription and not plan_financing:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Consumable {consumable.id}: No subscription or plan_financing found in scheduler {scheduler.id}, skipping"
                            )
                        )
                        skipped_count += 1
                        continue

                    if subscription:
                        action_msg = (
                            f"Consumable {consumable.id}: Would set subscription={subscription.id} "
                            f"(from {source}, service stock {scheduler.id}, valid_until={consumable.valid_until})"
                        )
                    else:
                        action_msg = (
                            f"Consumable {consumable.id}: Would set plan_financing={plan_financing.id} "
                            f"(from {source}, service stock {scheduler.id}, valid_until={consumable.valid_until})"
                        )

                    if dry_run:
                        self.stdout.write(self.style.SUCCESS(f"[DRY RUN] {action_msg}"))
                        would_update_ids.append(consumable.id)
                        would_update_details.append(
                            {
                                "consumable_id": consumable.id,
                                "subscription_id": getattr(subscription, "id", None),
                                "plan_financing_id": getattr(plan_financing, "id", None),
                                "scheduler_id": scheduler.id,
                                "source": source,
                            }
                        )
                    else:
                        # Use queryset update to avoid triggering post_save signals (e.g., auto-recharge checks)
                        Consumable.objects.filter(id=consumable.id).update(
                            subscription=subscription, plan_financing=plan_financing
                        )
                        self.stdout.write(self.style.SUCCESS(action_msg.replace("Would set", "Set")))
                        updated_ids.append(consumable.id)
                        updated_details.append(
                            {
                                "consumable_id": consumable.id,
                                "subscription_id": getattr(subscription, "id", None),
                                "plan_financing_id": getattr(plan_financing, "id", None),
                                "scheduler_id": scheduler.id,
                                "source": source,
                            }
                        )

                    updated_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Consumable {consumable.id}: Error - {str(e)}"))
                    error_count += 1

            # Progress update after each batch
            processed = min(i + batch_size, total_count)
            self.stdout.write(f"Processed {processed}/{total_count} consumables...")

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"  Total found: {total_count}\n"
                f"  {'Would update' if dry_run else 'Updated'}: {updated_count}\n"
                f"  Skipped (no scheduler): {skipped_count}\n"
                f"  Skipped (not in consumables list): {not_in_list_count}\n"
                f"  Skipped (valid_until mismatch): {mismatch_count}\n"
                f"  Skipped (expired): {expired_count}\n"
                f"  Errors: {error_count}"
            )
        )

        if dry_run and would_update_ids:
            ids_str = ", ".join(str(x) for x in would_update_ids)
            self.stdout.write(self.style.WARNING(f"Would update IDs: [{ids_str}]"))
            if would_update_details:
                self.stdout.write(self.style.WARNING("Would update details:"))
                for d in would_update_details:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  - consumable={d['consumable_id']} -> subscription={d['subscription_id']} "
                            f"plan_financing={d['plan_financing_id']} scheduler={d['scheduler_id']} source={d['source']}"
                        )
                    )
        elif not dry_run and updated_ids:
            ids_str = ", ".join(str(x) for x in updated_ids)
            self.stdout.write(self.style.SUCCESS(f"Updated IDs: [{ids_str}]"))
            if updated_details:
                self.stdout.write(self.style.SUCCESS("Updated details:"))
                for d in updated_details:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  - consumable={d['consumable_id']} -> subscription={d['subscription_id']} "
                            f"plan_financing={d['plan_financing_id']} scheduler={d['scheduler_id']} source={d['source']}"
                        )
                    )

        if expired_count > 0 and not include_expired:
            self.stdout.write(
                self.style.WARNING(
                    f"\nNote: {expired_count} expired consumables were skipped. "
                    f"Use --include-expired to process them."
                )
            )
