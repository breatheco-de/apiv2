"""
Management command to backfill syllabus field on Answer and Review models.

This command populates the syllabus field based on the cohort's syllabus_version
for existing Answer and Review records that have a cohort but no syllabus set.

Usage:
    python manage.py backfill_feedback_syllabus
    python manage.py backfill_feedback_syllabus --dry-run
    python manage.py backfill_feedback_syllabus --model answer
    python manage.py backfill_feedback_syllabus --model review
"""

from django.core.management.base import BaseCommand

from breathecode.feedback.models import Answer, Review


class Command(BaseCommand):
    help = "Backfill syllabus field on Answer and Review models based on cohort's syllabus_version"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--model",
            type=str,
            choices=["answer", "review", "all"],
            default="all",
            help="Which model to update (answer, review, or all)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of records to process",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        model_choice = options["model"]
        limit = options["limit"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        total_updated = 0

        # Process Answer model
        if model_choice in ["answer", "all"]:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.MIGRATE_HEADING("Processing Answer model..."))
            self.stdout.write("=" * 70)
            updated = self._process_answers(dry_run, limit)
            total_updated += updated

        # Process Review model
        if model_choice in ["review", "all"]:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.MIGRATE_HEADING("Processing Review model..."))
            self.stdout.write("=" * 70)
            updated = self._process_reviews(dry_run, limit)
            total_updated += updated

        # Summary
        self.stdout.write("\n" + "=" * 70)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would update {total_updated} records in total")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully updated {total_updated} records in total")
            )
        self.stdout.write("=" * 70 + "\n")

    def _process_answers(self, dry_run, limit):
        """Process Answer records."""

        # Find answers that have a cohort but no syllabus set
        # and where the cohort has a syllabus_version with a syllabus
        answers = Answer.objects.filter(
            cohort__isnull=False,
            syllabus__isnull=True,
            cohort__syllabus_version__isnull=False,
            cohort__syllabus_version__syllabus__isnull=False,
        ).select_related("cohort__syllabus_version__syllabus")

        if limit:
            answers = answers[:limit]

        total_count = answers.count()
        self.stdout.write(f"Found {total_count} Answer records to process")

        if total_count == 0:
            self.stdout.write(self.style.WARNING("  No answers need updating"))
            return 0

        updated_count = 0
        errors = []

        for answer in answers:
            try:
                syllabus = answer.cohort.syllabus_version.syllabus

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] Answer {answer.id}: "
                        f"cohort={answer.cohort.slug} → syllabus={syllabus.slug}"
                    )
                else:
                    answer.syllabus = syllabus
                    answer.save(update_fields=["syllabus"])
                    self.stdout.write(
                        f"  ✓ Answer {answer.id}: "
                        f"cohort={answer.cohort.slug} → syllabus={syllabus.slug}"
                    )

                updated_count += 1

            except Exception as e:
                error_msg = f"Answer {answer.id}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ✗ {error_msg}"))

        # Summary for answers
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would update {updated_count} Answer records")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} Answer records")
            )

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(errors) > 5:
                self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 5} more"))

        return updated_count

    def _process_reviews(self, dry_run, limit):
        """Process Review records."""

        # Find reviews that have a cohort but no syllabus set
        # and where the cohort has a syllabus_version with a syllabus
        reviews = Review.objects.filter(
            cohort__isnull=False,
            syllabus__isnull=True,
            cohort__syllabus_version__isnull=False,
            cohort__syllabus_version__syllabus__isnull=False,
        ).select_related("cohort__syllabus_version__syllabus")

        if limit:
            reviews = reviews[:limit]

        total_count = reviews.count()
        self.stdout.write(f"Found {total_count} Review records to process")

        if total_count == 0:
            self.stdout.write(self.style.WARNING("  No reviews need updating"))
            return 0

        updated_count = 0
        errors = []

        for review in reviews:
            try:
                syllabus = review.cohort.syllabus_version.syllabus

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] Review {review.id}: "
                        f"cohort={review.cohort.slug} → syllabus={syllabus.slug}"
                    )
                else:
                    review.syllabus = syllabus
                    review.save(update_fields=["syllabus"])
                    self.stdout.write(
                        f"  ✓ Review {review.id}: "
                        f"cohort={review.cohort.slug} → syllabus={syllabus.slug}"
                    )

                updated_count += 1

            except Exception as e:
                error_msg = f"Review {review.id}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ✗ {error_msg}"))

        # Summary for reviews
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would update {updated_count} Review records")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} Review records")
            )

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(errors) > 5:
                self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 5} more"))

        return updated_count

