from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from breathecode.admissions.models import Academy
from breathecode.payments import actions
from breathecode.payments.models import Coupon


class Command(BaseCommand):
    help = "Calculate and cleanup coupon statistics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy-id",
            type=int,
            default=None,
            help="Process only a specific academy (default: all academies)",
        )
        parser.add_argument(
            "--skip-cleanup",
            action="store_true",
            help="Skip cleanup of stale stats",
        )
        parser.add_argument(
            "--skip-calculation",
            action="store_true",
            help="Skip calculation of recent stats",
        )

    def handle(self, *args, **options):
        academy_id = options.get("academy_id")
        skip_cleanup = options.get("skip_cleanup", False)
        skip_calculation = options.get("skip_calculation", False)

        if not skip_calculation:
            self.stdout.write("Calculating recent coupon stats...")
            self.calculate_recent_coupon_stats(academy_id)
            self.stdout.write(self.style.SUCCESS("Recent stats calculation completed"))

        if not skip_cleanup:
            self.stdout.write("Cleaning up stale coupon stats...")
            self.cleanup_stale_coupon_stats(academy_id)
            self.stdout.write(self.style.SUCCESS("Stale stats cleanup completed"))

    def calculate_recent_coupon_stats(self, academy_id=None):
        """
        Calculate detailed stats for recently active coupons, processing per academy.
        
        Processes coupons that:
        - Have been used at least stats_min_usage times
        - Were used within stats_hours_threshold hours
        - Are associated with the academy's plans (or global plans)
        
        Uses academy-specific feature_flags.coupons config merged with defaults.
        Global plans (owner=None) are processed once using default config to avoid redundancy.
        """
        total_processed = 0
        total_errors = 0

        # Process global plans once (using default config)
        # Only process coupons that have global plans AND no academy-specific plans
        if academy_id is None:
            self.stdout.write("Processing global-only coupons (owner=None) with default config")
            try:
                default_config = actions.get_coupon_stats_config(None)
                coupons_config = default_config.get("coupons", {})

                hours_threshold = coupons_config.get("stats_hours_threshold", 24)
                top_n = coupons_config.get("stats_top_n", 100)
                min_usage = coupons_config.get("stats_min_usage", 2)

                cutoff_time = timezone.now() - timedelta(hours=hours_threshold)

                # Coupons that have global plans but NO academy-specific plans
                # This ensures we don't process the same coupon multiple times
                global_coupons = (
                    Coupon.objects.filter(
                        plans__owner=None,
                        times_used__gte=min_usage,
                        last_used_at__gte=cutoff_time,
                    )
                    .exclude(plans__owner__isnull=False)  # Exclude if has any academy-specific plans
                    .distinct()
                    .order_by("-times_used", "-last_used_at")[:top_n]
                )

                count = global_coupons.count()
                if count > 0:
                    self.stdout.write(
                        f"Global plans: Processing {count} recently active coupons "
                        f"(used in last {hours_threshold}h, min_usage={min_usage})"
                    )

                    for coupon in global_coupons:
                        try:
                            stats = actions.calculate_single_coupon_stats(coupon)
                            coupon.stats = stats
                            coupon.stats_updated_at = timezone.now()
                            coupon.save(update_fields=["stats", "stats_updated_at"])
                            total_processed += 1
                        except Exception as e:
                            total_errors += 1
                            self.stdout.write(
                                self.style.ERROR(f"Error calculating stats for global coupon {coupon.slug}: {e}")
                            )
                            continue

                    self.stdout.write(f"Global plans: Successfully processed {count} coupons")
            except Exception as e:
                total_errors += 1
                self.stdout.write(self.style.ERROR(f"Error processing global plans: {e}"))

        # Process academy-specific plans
        if academy_id:
            academies = Academy.objects.filter(id=academy_id)
        else:
            academies = Academy.objects.all()

        for academy in academies:
            try:
                # Get academy-specific config
                config = actions.get_coupon_stats_config(academy.id)
                coupons_config = config.get("coupons", {})

                hours_threshold = coupons_config.get("stats_hours_threshold", 24)
                top_n = coupons_config.get("stats_top_n", 100)
                min_usage = coupons_config.get("stats_min_usage", 2)

                cutoff_time = timezone.now() - timedelta(hours=hours_threshold)

                # Coupons associated with this academy's plans
                # This includes coupons that may also have global plans (they'll be processed per academy)
                academy_coupons = (
                    Coupon.objects.filter(
                        plans__owner__id=academy.id,
                        times_used__gte=min_usage,
                        last_used_at__gte=cutoff_time,
                    )
                    .distinct()
                    .order_by("-times_used", "-last_used_at")[:top_n]
                )

                count = academy_coupons.count()
                self.stdout.write(
                    f"Academy {academy.id} ({academy.slug}): Processing {count} recently active coupons "
                    f"(used in last {hours_threshold}h, min_usage={min_usage})"
                )

                if count == 0:
                    continue

                for coupon in academy_coupons:
                    try:
                        stats = actions.calculate_single_coupon_stats(coupon)
                        coupon.stats = stats
                        coupon.stats_updated_at = timezone.now()
                        coupon.save(update_fields=["stats", "stats_updated_at"])
                        total_processed += 1
                    except Exception as e:
                        total_errors += 1
                        self.stdout.write(
                            self.style.ERROR(f"Error calculating stats for coupon {coupon.slug}: {e}")
                        )
                        continue

                self.stdout.write(f"Academy {academy.id}: Successfully processed {count} coupons")

            except Exception as e:
                total_errors += 1
                self.stdout.write(self.style.ERROR(f"Error processing academy {academy.id}: {e}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"calculate_recent_coupon_stats completed: {total_processed} processed, {total_errors} errors"
            )
        )

    def cleanup_stale_coupon_stats(self, academy_id=None):
        """
        Remove stats from coupons that haven't been used recently, processing per academy.
        
        Uses academy-specific feature_flags.coupons.stats_cleanup_threshold config.
        Global plans (owner=None) are processed once using default config to avoid redundancy.
        """
        total_cleaned = 0

        # Process global plans once (using default config)
        if academy_id is None:
            self.stdout.write("Cleaning up stale stats for global plans (owner=None) with default config")
            try:
                default_config = actions.get_coupon_stats_config(None)
                coupons_config = default_config.get("coupons", {})

                cleanup_threshold = coupons_config.get("stats_cleanup_threshold", 24 * 730)  # Default: 2 years
                cutoff_time = timezone.now() - timedelta(hours=cleanup_threshold)

                # Coupons that have global plans but NO academy-specific plans
                stale_global_coupons = Coupon.objects.filter(
                    plans__owner=None,
                    stats__isnull=False,
                    last_used_at__lt=cutoff_time,
                ).exclude(plans__owner__isnull=False).distinct()  # Exclude if has any academy-specific plans

                count = stale_global_coupons.count()
                if count > 0:
                    self.stdout.write(
                        f"Global plans: Cleaning up stats for {count} stale coupons "
                        f"(not used in last {cleanup_threshold/24:.0f} days)"
                    )
                    stale_global_coupons.update(stats=None, stats_updated_at=None)
                    total_cleaned += count
                else:
                    self.stdout.write("Global plans: No stale coupon stats to clean up")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cleaning up stats for global plans: {e}"))

        # Process academy-specific plans
        if academy_id:
            academies = Academy.objects.filter(id=academy_id)
        else:
            academies = Academy.objects.all()

        for academy in academies:
            try:
                # Get academy-specific config
                config = actions.get_coupon_stats_config(academy.id)
                coupons_config = config.get("coupons", {})

                cleanup_threshold = coupons_config.get("stats_cleanup_threshold", 24 * 730)  # Default: 2 years
                cutoff_time = timezone.now() - timedelta(hours=cleanup_threshold)

                # Coupons associated with this academy's plans
                # This includes coupons that may also have global plans
                stale_coupons = Coupon.objects.filter(
                    plans__owner__id=academy.id,
                    stats__isnull=False,
                    last_used_at__lt=cutoff_time,
                ).distinct()

                count = stale_coupons.count()
                if count > 0:
                    self.stdout.write(
                        f"Academy {academy.id} ({academy.slug}): Cleaning up stats for {count} stale coupons "
                        f"(not used in last {cleanup_threshold/24:.0f} days)"
                    )
                    stale_coupons.update(stats=None, stats_updated_at=None)
                    total_cleaned += count
                else:
                    self.stdout.write(f"Academy {academy.id}: No stale coupon stats to clean up")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cleaning up stats for academy {academy.id}: {e}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(f"cleanup_stale_coupon_stats completed: {total_cleaned} coupons cleaned")
        )

