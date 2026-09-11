import pytest
from django.core.management.base import CommandError

from breathecode.assignments.management.commands.apply_learnpack_telemetry_to_cohort_tasks import Command
from breathecode.assignments.models import AssignmentTelemetry, Task


@pytest.mark.django_db
def test_command_marks_pending_exercise_done_from_telemetry(database):
    model = database.create(
        user=1,
        cohort={"slug": "new-cohort"},
        task={"associated_slug": "speaking-with-ai", "task_type": "EXERCISE", "title": "Speaking"},
    )
    telemetry = AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug="speaking-with-ai",
        completion_rate=100,
        telemetry={"slug": "speaking-with-ai"},
    )

    Command().handle(cohort=model.cohort.slug, user=None, dry_run=False)

    task = Task.objects.get(id=model.task.id)
    assert task.task_status == "DONE"
    assert task.revision_status == "APPROVED"
    assert task.telemetry_id == telemetry.id


@pytest.mark.django_db
def test_command_dry_run_does_not_write(database):
    model = database.create(
        user=1,
        cohort={"slug": "new-cohort"},
        task={"associated_slug": "speaking-with-ai", "task_type": "EXERCISE", "title": "Speaking"},
    )
    AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug="speaking-with-ai",
        completion_rate=100,
        telemetry={"slug": "speaking-with-ai"},
    )

    Command().handle(cohort=str(model.cohort.id), user=None, dry_run=True)

    task = Task.objects.get(id=model.task.id)
    assert task.task_status == "PENDING"
    assert task.telemetry_id is None


@pytest.mark.django_db
def test_command_raises_when_cohort_is_missing(database):
    with pytest.raises(CommandError, match="Cohort not found"):
        Command().handle(cohort="does-not-exist", user=None, dry_run=True)
