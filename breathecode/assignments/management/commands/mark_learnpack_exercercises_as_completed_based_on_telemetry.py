from django.core.management.base import BaseCommand
from django.utils import timezone
from breathecode.assignments.models import AssignmentTelemetry, Task


class Command(BaseCommand):
    help = 'Mark learnpack exercises as completed based on telemetry completion rate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--completion-threshold',
            type=float,
            default=99.999,
            help='Completion rate threshold to mark as done (default: 99.999)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        completion_threshold = options['completion_threshold']
        dry_run = options['dry_run']
        
        # Get all telemetries with completion rate
        telemetries = AssignmentTelemetry.objects.filter(
            completion_rate__isnull=False
        ).select_related('user')
        
        self.stdout.write(f"Processing {telemetries.count()} telemetries...")
        
        updated_tasks = 0
        completed_tasks = 0
        pending_tasks = 0
        
        for telemetry in telemetries:
            # Get all tasks associated with this telemetry's asset_slug and user
            asset_tasks = Task.objects.filter(
                associated_slug=telemetry.asset_slug,
                user=telemetry.user
            )
            
            if asset_tasks.count() == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"No tasks found for user {telemetry.user.id} and asset {telemetry.asset_slug}"
                    )
                )
                continue
            
            # Check if completion rate meets threshold
            if telemetry.completion_rate >= completion_threshold:
                # Mark as completed
                for task in asset_tasks:
                    if dry_run:
                        self.stdout.write(
                            f"Would mark task {task.id} ({task.title}) as DONE - "
                            f"completion rate: {telemetry.completion_rate}%"
                        )
                    else:
                        task.task_status = Task.TaskStatus.DONE
                        task.revision_status = Task.RevisionStatus.APPROVED
                        task.description = "You have completed all steps on this exercise"
                        task.delivered_at = timezone.now()
                        task.reviewed_at = timezone.now()
                        task.save()
                        self.stdout.write(
                            f"Marked task {task.id} ({task.title}) as DONE - "
                            f"completion rate: {telemetry.completion_rate}%"
                        )
                    completed_tasks += 1
                    updated_tasks += 1
            else:
                # Mark as pending
                for task in asset_tasks:
                    if dry_run:
                        self.stdout.write(
                            f"Would mark task {task.id} ({task.title}) as PENDING - "
                            f"completion rate: {telemetry.completion_rate}%"
                        )
                    else:
                        task.task_status = Task.TaskStatus.PENDING
                        task.revision_status = Task.RevisionStatus.PENDING
                        task.description = ""
                        task.delivered_at = None
                        task.reviewed_at = timezone.now()
                        task.save()
                        self.stdout.write(
                            f"Marked task {task.id} ({task.title}) as PENDING - "
                            f"completion rate: {telemetry.completion_rate}%"
                        )
                    pending_tasks += 1
                    updated_tasks += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: Would update {updated_tasks} tasks "
                    f"({completed_tasks} completed, {pending_tasks} pending)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated {updated_tasks} tasks "
                    f"({completed_tasks} completed, {pending_tasks} pending)"
                )
            )
