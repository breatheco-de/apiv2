"""
Django command to normalize white_label_features for all academies.

This command merges the current white_label_features of each academy with the
latest defaults, ensuring all academies have the newest feature flags.

Usage:
    python manage.py normalize_white_label_features [--dry-run]
"""

from django.core.management.base import BaseCommand

from breathecode.admissions.models import Academy


class Command(BaseCommand):
    help = "Normalize white_label_features for all academies with latest defaults"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually saving",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        academies = Academy.objects.all()
        total = academies.count()
        updated = 0

        self.stdout.write(f"Found {total} academies to process")

        for academy in academies:
            # Get merged features
            merged_features = academy.get_white_label_features()

            # Check if there are differences
            if merged_features != academy.white_label_features:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"[DRY RUN] Would update academy {academy.id} ({academy.slug})")
                    )
                    self.stdout.write(f"  Current: {academy.white_label_features}")
                    self.stdout.write(f"  New:     {merged_features}")
                else:
                    academy.white_label_features = merged_features
                    academy.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated academy {academy.id} ({academy.slug})"))

                updated += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would update {updated} out of {total} academies. Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated} out of {total} academies"))
