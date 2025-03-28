import io
import logging
import os
from contextlib import redirect_stdout
from datetime import timedelta

from celery.result import AsyncResult
from django.core.management.base import BaseCommand
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone
from task_manager.models import TaskManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check for task status discrepancies between Celery Task Manager and actual execution"

    output_buffer = io.StringIO()

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=906, help="Number of hours to look back for stuck tasks")
        parser.add_argument("--check-execution", action="store_true", help="Verify actual task execution")
        parser.add_argument("--limit", type=int, default=5, help="Limit sample size for detailed checks")
        parser.add_argument("--log-file", type=str, help="Path to save output log file")

    def handle(self, *args, **options):
        hours = options["hours"]
        check_execution = options["check_execution"]
        limit = options["limit"]
        log_file = options.get("log_file")
        now = timezone.now()
        time_threshold = now - timedelta(hours=hours)

        # Use output redirection if log file is specified
        if log_file:
            with redirect_stdout(self.output_buffer):
                self._handle_logic(hours, check_execution, limit, now, time_threshold)

            # Write buffer to both console and file
            output = self.output_buffer.getvalue()
            self.stdout.write(output)

            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

            # Write to file
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(output)

            self.stdout.write(self.style.SUCCESS(f"\nLog saved to: {log_file}"))
        else:
            # Just run normally
            self._handle_logic(hours, check_execution, limit, now, time_threshold)

    def _handle_logic(self, hours, check_execution, limit, now, time_threshold):
        """Main command logic extracted to allow output redirection"""
        print(f"Starting task status check for tasks older than {hours} hours...")

        # Get tasks that have been stuck in SCHEDULED status
        print("Querying database for stuck tasks... This may take a moment")
        stuck_tasks = (
            TaskManager.objects.filter(Q(status="SCHEDULED") | Q(status="PENDING"), last_run__lte=time_threshold)
            .values("task_module", "task_name")
            .annotate(
                count=Count("id"),
                duration=ExpressionWrapper(now - F("last_run"), output_field=DurationField()),
            )
            .order_by("-count")
        )
        print("Database query complete")

        # Process the queryset results to calculate hours correctly
        processed_tasks = []
        for task in stuck_tasks:
            task_copy = task.copy()
            if isinstance(task["duration"], timedelta):
                # Convert timedelta to hours
                task_copy["max_hours"] = task["duration"].total_seconds() / 3600
            else:
                # Fallback if somehow it's not a timedelta
                task_copy["max_hours"] = 0
            processed_tasks.append(task_copy)

        # Sort by count and replace the original queryset results
        print(f"Found {len(processed_tasks)} stuck task types")
        processed_tasks.sort(key=lambda x: x["count"], reverse=True)

        print(f"\nAnalyzing tasks stuck for more than {hours} hours:")
        print("=" * 80)

        # Add task type counter and limit to top tasks if too many
        task_count = min(len(processed_tasks), 20)  # Limit to top 20 task types
        print(f"Showing top {task_count} task types (out of {len(processed_tasks)})")

        for i, task in enumerate(processed_tasks[:task_count]):
            print(
                f"\nTask {i+1}/{task_count}: {task['task_module']}.{task['task_name']}\n"
                f"Count: {task['count']}\n"
                f"Max Hours Stuck: {task['max_hours']:.2f}\n"
            )

            # Get sample of stuck tasks for this task type
            sample_tasks = TaskManager.objects.filter(
                status="SCHEDULED",
                task_module=task["task_module"],
                task_name=task["task_name"],
                last_run__lte=time_threshold,
            ).order_by("-last_run")[:limit]

            if len(sample_tasks) > 0:
                print(f"Showing {len(sample_tasks)} sample tasks:")

                print("\nSample Tasks:")
                for sample in sample_tasks:
                    print(
                        f"ID: {sample.id}\n"
                        f"Arguments: {sample.arguments}\n"
                        f"Last Run: {sample.last_run}\n"
                        f"Task ID: {sample.task_id}\n"
                        f"Status Message: {sample.status_message}\n"
                        f"Attempts: {sample.attempts}\n"
                    )

                    # Check if task was actually executed by examining Celery task state
                    if check_execution and sample.task_id:
                        try:
                            result = AsyncResult(sample.task_id)
                            print(f"Celery Task State: {result.state}")
                            if result.state == "SUCCESS":
                                print("Task executed successfully in Celery but TaskManager not updated!")
                            elif result.state == "FAILURE":
                                print(f"Task failed in Celery: {result.traceback}")
                        except Exception as e:
                            print(f"Could not fetch Celery task state: {str(e)}")

                        # Try to verify if task function was actually executed based on its expected effects
                        self.verify_task_execution(sample)

                    print("-" * 40)
            else:
                print("No sample tasks found")

        # Check for tasks that might be stuck in other states
        print("Checking for tasks stuck in other states...")
        other_stuck = (
            TaskManager.objects.filter(
                ~Q(status__in=["DONE", "CANCELLED", "REVERSED", "ERROR", "ABORTED"]), last_run__lte=time_threshold
            )
            .values("status")
            .annotate(count=Count("id"))
        )

        if other_stuck:
            print("\nOther potentially stuck tasks by status:")
            print("=" * 80)
            for status in other_stuck:
                print(f"Status: {status['status']}, Count: {status['count']}")
        else:
            print("No tasks stuck in other states")

        # Recommendations
        print("\nRecommendations:")
        print("=" * 80)
        if processed_tasks:
            print(
                "\n1. Check Celery workers are running and processing tasks\n"
                "2. Verify Redis connection and queue status\n"
                "3. Look for any error patterns in the sample tasks\n"
                "4. Consider resetting stuck tasks or investigating specific task modules\n"
                "5. Check if the task_manager and actual task function are properly communicating status updates\n"
                "6. For tasks with successful Celery execution but pending TaskManager status, update the TaskManager database"
            )
        else:
            print("\nNo significant task status issues found")

        print("Task status check complete!")

    def verify_task_execution(self, task):
        """Verify task execution by checking related model changes"""
        module_name = task.task_module
        task_name = task.task_name
        arguments = task.arguments

        # Only print for specific verification checks we're actually doing
        verification_done = False

        # Special checks based on task type
        if module_name == "breathecode.assignments.tasks" and task_name == "async_learnpack_webhook":
            # Check if webhook was processed
            if "webhook_id" in arguments:
                webhook_id = arguments.get("webhook_id")
                verification_done = True
                print(f"Verifying webhook (ID: {webhook_id}):")
                try:
                    # Try to import LearnPackWebhook
                    from breathecode.assignments.models import LearnPackWebhook

                    # Use getattr to check if fields exist
                    webhook = LearnPackWebhook.objects.filter(id=webhook_id).first()
                    if webhook:
                        status = getattr(webhook, "status", None)
                        status_text = getattr(webhook, "status_text", None)
                        print(f"Webhook Status: {status}")
                        if status == "DONE":
                            print("Webhook was processed successfully but TaskManager not updated!")
                        elif status == "ERROR":
                            print(f"Webhook processing failed: {status_text}")
                    else:
                        print("Webhook not found - may have been deleted")
                except Exception as e:
                    print(f"Error checking webhook: {str(e)}")

        elif module_name == "breathecode.notify.tasks" and task_name == "async_deliver_hook":
            # Check if hook was delivered
            if "hook_id" in arguments:
                hook_id = arguments.get("hook_id")
                verification_done = True
                print(f"Verifying hook (ID: {hook_id}):")
                try:
                    # Try to import Hook model
                    from breathecode.notify.models import Hook

                    hook = Hook.objects.filter(id=hook_id).first()
                    if hook:
                        status = getattr(hook, "status", None)
                        status_text = getattr(hook, "status_text", None)
                        print(f"Hook Status: {status}")
                        if status in ["DONE", "DELIVERED", "SUCCESS"]:
                            print("Hook was delivered successfully but TaskManager not updated!")
                        elif status in ["ERROR", "FAILED"]:
                            print(f"Hook delivery failed: {status_text or 'No details'}")
                    else:
                        print("Hook not found - may have been deleted")
                except Exception as e:
                    print(f"Error checking hook: {str(e)}")

        # Only print a generic verification message if we didn't do any specific verifications
        if not verification_done:
            print(f"No specific verification available for {module_name}.{task_name}")

        else:
            print(f"Verification complete for {module_name}.{task_name}")
