from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from breathecode.admissions.models import Cohort


class Command(BaseCommand):
    help = "Backfill liveclass_date in cohort history_log from updated_at"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without saving changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        cohorts = Cohort.objects.exclude(history_log__isnull=True).exclude(history_log={})
        total_cohorts = cohorts.count()
        updated_cohorts = 0
        total_days_updated = 0

        self.stdout.write(f"Found {total_cohorts} cohorts with history_log")

        for cohort in cohorts:
            if not cohort.history_log or not isinstance(cohort.history_log, dict):
                continue

            history_log_updated = False
            days_updated = 0

            for day_key, day_data in cohort.history_log.items():
                if not isinstance(day_data, dict):
                    continue

                # Check if day has updated_at but no liveclass_date
                if "updated_at" in day_data and (
                    "liveclass_date" not in day_data or day_data.get("liveclass_date") is None
                ):
                    # Parse updated_at to ensure it's a valid datetime string
                    updated_at_str = day_data["updated_at"]
                    parsed_date = parse_datetime(updated_at_str)

                    if parsed_date:
                        day_data["liveclass_date"] = updated_at_str
                        history_log_updated = True
                        days_updated += 1
                        self.stdout.write(
                            f"  Cohort {cohort.slug} (ID: {cohort.id}), Day {day_key}: "
                            f"Added liveclass_date from updated_at"
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Cohort {cohort.slug} (ID: {cohort.id}), Day {day_key}: "
                                f"Could not parse updated_at: {updated_at_str}"
                            )
                        )

            if history_log_updated:
                if not dry_run:
                    cohort.save(update_fields=["history_log"])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Saved cohort {cohort.slug} (ID: {cohort.id}) - {days_updated} days updated"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would save cohort {cohort.slug} (ID: {cohort.id}) - {days_updated} days updated"
                        )
                    )
                updated_cohorts += 1
                total_days_updated += days_updated

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'[DRY RUN] ' if dry_run else ''}Summary: "
                f"{updated_cohorts}/{total_cohorts} cohorts updated, "
                f"{total_days_updated} total days updated"
            )
        )

