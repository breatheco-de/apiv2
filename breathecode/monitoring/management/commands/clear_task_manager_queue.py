from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count
from task_manager.models import TaskManager


class Command(BaseCommand):
    help = "Clear TaskManager records from the database with optimal performance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            choices=["PENDING", "DONE", "CANCELLED", "REVERSED", "PAUSED", "ABORTED", "ERROR", "SCHEDULED", "ALL"],
            help="Status of TaskManager records to clear (optional, filters by status if specified)"
        )
        parser.add_argument(
            "--task-module",
            type=str,
            help="Filter by specific task module (e.g., 'breathecode.notify.tasks')"
        )
        parser.add_argument(
            "--task-name",
            type=str,
            help="Filter by specific task name (e.g., 'async_deliver_hook')"
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

    def _build_queryset(self, status, task_module, task_name):
        """
        Build the queryset based on the provided filters
        """
        queryset = TaskManager.objects.all()
        
        # Only apply status filter if it's explicitly specified
        if status and status != "ALL":
            queryset = queryset.filter(status=status)
        
        if task_module:
            queryset = queryset.filter(task_module=task_module)
            
        if task_name:
            queryset = queryset.filter(task_name=task_name)
            
        return queryset

    def handle(self, *args, **options):
        status = options["status"]
        task_module = options["task_module"]
        task_name = options["task_name"]
        dry_run = options["dry_run"]
        force = options["force"]
        show_summary = options["show_summary"]
        use_cursor = options["use_cursor"]

        # Build the queryset for counting
        queryset = self._build_queryset(status, task_module, task_name)
        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING(f"No TaskManager records found with the specified criteria")
            )
            
            if show_summary:
                self._show_status_summary()
            return

        # Show summary of what will be deleted
        self.stdout.write(
            self.style.SUCCESS(f"Found {total_count} TaskManager records to delete")
        )
        
        if task_module:
            self.stdout.write(f"Task Module: {task_module}")
        if task_name:
            self.stdout.write(f"Task Name: {task_name}")
        if status:
            self.stdout.write(f"Status: {status}")
        else:
            self.stdout.write("Status: ALL (no status filter applied)")

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("DRY RUN MODE - No records will be deleted")
            )
            return

        # Confirmation prompt
        if not force:
            confirm = input(
                f"Are you sure you want to delete {total_count} TaskManager records? (yes/no): "
            )
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(self.style.WARNING("Operation cancelled"))
                return

        # Perform deletion with optimal performance
        if use_cursor or total_count > 50000:
            # Use cursor for large datasets or when explicitly requested
            deleted_count = self._delete_with_cursor(status, task_module, task_name, total_count)
        else:
            # Use Django ORM for smaller datasets
            deleted_count = self._delete_with_orm(queryset)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} TaskManager records"
            )
        )

    def _delete_with_cursor(self, status, task_module, task_name, total_count):
        """
        Delete records using raw SQL cursor for maximum performance
        """
        self.stdout.write("Using raw SQL cursor for maximum performance...")
        
        with connection.cursor() as cursor:
            # Build the WHERE clause dynamically
            where_conditions = []
            params = []
            
            if status != "ALL":
                where_conditions.append("status = %s")
                params.append(status)
            
            if task_module:
                where_conditions.append("task_module = %s")
                params.append(task_module)
                
            if task_name:
                where_conditions.append("task_name = %s")
                params.append(task_name)
            
            # Build the SQL query
            if where_conditions:
                sql = f"DELETE FROM task_manager_taskmanager WHERE {' AND '.join(where_conditions)}"
            else:
                sql = "DELETE FROM task_manager_taskmanager"
                params = []
            
            self.stdout.write(f"Executing: {sql}")
            if params:
                self.stdout.write(f"Parameters: {params}")
            
            cursor.execute(sql, params)
            deleted_count = cursor.rowcount
            
            self.stdout.write(f"Deleted {deleted_count} records using raw SQL")
        
        return deleted_count

    def _delete_with_orm(self, queryset):
        """
        Delete records using Django ORM (for smaller datasets)
        """
        self.stdout.write("Using Django ORM for deletion...")
        
        deleted_count = queryset.delete()[0]
        self.stdout.write(f"Deleted {deleted_count} records using Django ORM")
        
        return deleted_count

    def _show_status_summary(self):
        """
        Show summary of TaskManager records by status
        """
        status_counts = (
            TaskManager.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        self.stdout.write("\nCurrent TaskManager status summary:")
        self.stdout.write("-" * 50)
        
        for status_info in status_counts:
            status = status_info["status"]
            count = status_info["count"]
            self.stdout.write(f"{status}: {count:,} records")
        
        self.stdout.write("-" * 50)
        total = sum(status_info["count"] for status_info in status_counts)
        self.stdout.write(f"Total: {total:,} records")

        # Show task module summary
        self.stdout.write("\nTask Module Summary:")
        self.stdout.write("-" * 50)
        module_counts = (
            TaskManager.objects.values("task_module")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]  # Top 10 modules
        )
        
        for module_info in module_counts:
            module = module_info["task_module"]
            count = module_info["count"]
            self.stdout.write(f"{module}: {count:,} records")
        
        if TaskManager.objects.count() > 10:
            self.stdout.write("... (showing top 10 modules)")
