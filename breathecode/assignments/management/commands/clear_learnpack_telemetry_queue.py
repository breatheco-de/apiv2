from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.db.models import Count
from breathecode.assignments.models import LearnPackWebhook, PENDING, DONE, IGNORED, ERROR


class Command(BaseCommand):
    help = "Clear LearnPackWebhook records from the database with optimal performance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            choices=["PENDING", "DONE", "IGNORED", "ERROR", "ALL"],
            default="PENDING",
            help="Status of LearnPackWebhook records to clear (default: PENDING)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10000,
            help="Batch size for deletion to avoid timeouts (default: 10000)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion without confirmation prompt"
        )
        parser.add_argument(
            "--show-summary",
            action="store_true",
            help="Show status summary even when no records are found"
        )
        parser.add_argument(
            "--use-cursor",
            action="store_true",
            help="Use raw SQL cursor for maximum performance (default: True for large datasets)"
        )

    def handle(self, *args, **options):
        status = options["status"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        force = options["force"]
        show_summary = options["show_summary"]
        use_cursor = options["use_cursor"]

        # Get the count of records to be deleted
        if status == "ALL":
            queryset = LearnPackWebhook.objects.all()
        else:
            queryset = LearnPackWebhook.objects.filter(status=status)

        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING(f"No LearnPackWebhook records found with status '{status}'")
            )
            
            if show_summary:
                self._show_status_summary()
            return

        # Show summary
        self.stdout.write(
            self.style.SUCCESS(f"Found {total_count} LearnPackWebhook records with status '{status}'")
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("DRY RUN MODE - No records will be deleted")
            )
            return

        # Confirmation prompt
        if not force:
            confirm = input(
                f"Are you sure you want to delete {total_count} LearnPackWebhook records with status '{status}'? (yes/no): "
            )
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(self.style.WARNING("Operation cancelled"))
                return

        # Choose deletion method based on dataset size and user preference
        if use_cursor or total_count > 50000:
            # Use cursor for large datasets or when explicitly requested
            deleted_count = self._delete_with_cursor(status, total_count)
        else:
            # Use batch deletion for smaller datasets
            deleted_count = self._delete_records(queryset, batch_size, status)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} LearnPackWebhook records with status '{status}'"
            )
        )

    def _delete_with_cursor(self, status, total_count):
        """
        Delete records using raw SQL cursor for maximum performance
        """
        self.stdout.write("Using raw SQL cursor for maximum performance...")
        
        with connection.cursor() as cursor:
            if status == "ALL":
                sql = "DELETE FROM assignments_learnpackwebhook"
                params = []
            else:
                sql = "DELETE FROM assignments_learnpackwebhook WHERE status = %s"
                params = [status]
            
            self.stdout.write(f"Executing: {sql}")
            if params:
                self.stdout.write(f"Parameters: {params}")
            
            cursor.execute(sql, params)
            deleted_count = cursor.rowcount
            
            self.stdout.write(f"Deleted {deleted_count} records using raw SQL")
        
        return deleted_count

    def _delete_records(self, queryset, batch_size, status):
        """
        Delete records in batches for optimal performance (fallback method)
        """
        deleted_count = 0
        total_count = queryset.count()

        self.stdout.write(f"Starting deletion in batches of {batch_size}...")

        with transaction.atomic():
            while total_count > 0:
                # Get batch of IDs to delete
                batch_ids = list(
                    queryset.values_list("id", flat=True)[:batch_size]
                )

                if not batch_ids:
                    break

                # Delete batch using raw SQL for maximum performance
                batch_deleted = LearnPackWebhook.objects.filter(id__in=batch_ids).delete()[0]
                deleted_count += batch_deleted

                # Update progress
                remaining = total_count - deleted_count
                progress_percent = (deleted_count / total_count) * 100

                self.stdout.write(
                    f"Deleted {deleted_count}/{total_count} records ({progress_percent:.1f}%) - "
                    f"Remaining: {remaining}"
                )

                # Update total count for next iteration
                total_count = remaining

        return deleted_count

    def _show_status_summary(self):
        """
        Show summary of LearnPackWebhook records by status
        """
        status_counts = (
            LearnPackWebhook.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        self.stdout.write("\nCurrent LearnPackWebhook status summary:")
        self.stdout.write("-" * 40)
        
        for status_info in status_counts:
            status = status_info["status"]
            count = status_info["count"]
            self.stdout.write(f"{status}: {count:,} records")
        
        self.stdout.write("-" * 40)
        total = sum(status_info["count"] for status_info in status_counts)
        self.stdout.write(f"Total: {total:,} records")
