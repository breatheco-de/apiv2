"""
Management command to backfill academy field for tags using ActiveCampaign settings.

This command populates the academy field based on ac_academy.academy for existing
Tag records that have ac_academy but no academy set.

Usage:
    python manage.py backfill_tag_academy
    python manage.py backfill_tag_academy --dry-run
    python manage.py backfill_tag_academy --batch-size 50
    python manage.py backfill_tag_academy --limit 100
"""

from django.core.management.base import BaseCommand

from breathecode.marketing.models import Tag


class Command(BaseCommand):
    help = "Backfill academy field for tags using ActiveCampaign settings"

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
            help="Number of tags to process per batch (default: 100)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of tags to process",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options["limit"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Find tags with ac_academy but no academy set
        tags = Tag.objects.filter(
            ac_academy__isnull=False,
            academy__isnull=True,
        ).select_related("ac_academy__academy")

        if limit:
            tags = tags[:limit]

        total_count = tags.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No tags need updating"))
            return

        self.stdout.write(f"Found {total_count} tags to process")

        updated_count = 0
        skipped_count = 0
        errors = []

        # Process in batches
        for i in range(0, total_count, batch_size):
            batch = tags[i : i + batch_size]

            for tag in batch:
                try:
                    if not tag.ac_academy:
                        self.stdout.write(
                            self.style.WARNING(f"Tag {tag.id} ({tag.slug}): No ac_academy, skipping")
                        )
                        skipped_count += 1
                        continue

                    if not tag.ac_academy.academy:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Tag {tag.id} ({tag.slug}): ac_academy has no academy, skipping"
                            )
                        )
                        skipped_count += 1
                        continue

                    academy = tag.ac_academy.academy

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY RUN] Tag {tag.id} ({tag.slug}): "
                            f"ac_academy={tag.ac_academy.id} → academy={academy.id} ({academy.slug})"
                        )
                    else:
                        tag.academy = academy
                        tag.save(update_fields=["academy"])
                        self.stdout.write(
                            f"  ✓ Tag {tag.id} ({tag.slug}): "
                            f"ac_academy={tag.ac_academy.id} → academy={academy.id} ({academy.slug})"
                        )

                    updated_count += 1

                except Exception as e:
                    error_msg = f"Tag {tag.id} ({tag.slug}): {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f"  ✗ {error_msg}"))

            # Progress update after each batch
            processed = min(i + batch_size, total_count)
            self.stdout.write(f"Processed {processed}/{total_count} tags...")

        # Summary
        self.stdout.write("\n" + "=" * 70)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would update {updated_count} tags in total")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully updated {updated_count} tags in total"))
        self.stdout.write("=" * 70 + "\n")

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(errors) > 5:
                self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 5} more"))

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped_count} tags (missing ac_academy or academy)")
            )

