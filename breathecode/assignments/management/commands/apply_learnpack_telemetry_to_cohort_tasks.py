from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from breathecode.admissions.models import Cohort
from breathecode.assignments.actions import apply_existing_learnpack_telemetry
from breathecode.assignments.models import Task


class Command(BaseCommand):
    help = (
        "Relink LearnPack AssignmentTelemetry onto pending EXERCISE tasks of a cohort "
        "and mark them DONE when completion_rate is ~100%. "
        "Use after students were moved to a cohort that shares the same syllabus."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "cohort",
            type=str,
            help="Cohort id or slug whose pending exercises should be healed",
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Optional user id or email to limit the fix to one student",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without writing",
        )

    def handle(self, *args, **options):
        cohort_key = options["cohort"]
        dry_run = options["dry_run"]
        user_key = options["user"]

        cohort = self._get_cohort(cohort_key)
        tasks = Task.objects.filter(
            cohort=cohort,
            task_type=Task.TaskType.EXERCISE,
            task_status=Task.TaskStatus.PENDING,
        ).select_related("user")

        if user_key:
            user = self._get_user(user_key)
            tasks = tasks.filter(user=user)

        marked_done = 0
        linked_only = 0
        skipped = 0

        prefix = "DRY RUN: " if dry_run else ""
        self.stdout.write(f"{prefix}Scanning {tasks.count()} pending EXERCISE tasks in cohort {cohort.slug} ({cohort.id})")

        for task in tasks.iterator():
            previous_status = task.task_status
            previous_telemetry_id = task.telemetry_id
            apply_existing_learnpack_telemetry(task, persist=not dry_run)

            if task.task_status != previous_status:
                marked_done += 1
                self.stdout.write(
                    f"{prefix}Task {task.id} user={task.user_id} slug={task.associated_slug} -> DONE"
                )
            elif task.telemetry_id != previous_telemetry_id:
                linked_only += 1
                self.stdout.write(
                    f"{prefix}Task {task.id} user={task.user_id} slug={task.associated_slug} telemetry linked, still PENDING"
                )
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Done. marked_done={marked_done} telemetry_linked={linked_only} unchanged={skipped}"
            )
        )

    def _get_cohort(self, cohort_key: str) -> Cohort:
        if cohort_key.isdigit():
            cohort = Cohort.objects.filter(id=int(cohort_key)).first()
        else:
            cohort = Cohort.objects.filter(slug=cohort_key).first()

        if cohort is None:
            raise CommandError(f"Cohort not found: {cohort_key}")
        return cohort

    def _get_user(self, user_key: str) -> User:
        if user_key.isdigit():
            user = User.objects.filter(id=int(user_key)).first()
        else:
            user = User.objects.filter(email__iexact=user_key).first()

        if user is None:
            raise CommandError(f"User not found: {user_key}")
        return user
