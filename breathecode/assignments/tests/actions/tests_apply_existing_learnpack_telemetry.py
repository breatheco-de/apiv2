import pytest

from breathecode.assignments.actions import apply_existing_learnpack_telemetry
from breathecode.assignments.models import AssignmentTelemetry, Task


@pytest.mark.django_db
def test_links_telemetry_and_marks_exercise_done_when_completion_is_100(database):
    model = database.create(user=1, cohort=1)
    telemetry = AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug="speaking-with-ai",
        completion_rate=100,
        telemetry={"slug": "speaking-with-ai"},
    )
    task = Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug="speaking-with-ai",
        title="Speaking",
        task_type="EXERCISE",
        description="",
    )

    apply_existing_learnpack_telemetry(task)
    task.refresh_from_db()

    assert task.telemetry_id == telemetry.id
    assert task.task_status == Task.TaskStatus.DONE
    assert task.revision_status == Task.RevisionStatus.APPROVED
    assert task.delivered_at is not None


@pytest.mark.django_db
def test_links_canonical_telemetry_when_task_uses_translation_slug(database):
    model = database.create(
        user=1,
        cohort=1,
        asset=[
            {"slug": "speaking-with-ai", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "speaking-ais-language-structured-formats", "lang": "es", "asset_type": "EXERCISE"},
        ],
    )
    canonical = model.asset[0]
    translated = model.asset[1]
    translated.all_translations.add(canonical)

    telemetry = AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug=canonical.slug,
        completion_rate=100,
        telemetry={"slug": canonical.slug},
    )
    task = Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug=translated.slug,
        title="Speaking",
        task_type="EXERCISE",
        description="",
    )

    apply_existing_learnpack_telemetry(task)
    task.refresh_from_db()

    assert task.telemetry_id == telemetry.id
    assert task.task_status == Task.TaskStatus.DONE


@pytest.mark.django_db
def test_links_telemetry_but_keeps_pending_when_completion_is_low(database):
    model = database.create(user=1, cohort=1)
    telemetry = AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug="speaking-with-ai",
        completion_rate=40,
        telemetry={"slug": "speaking-with-ai"},
    )
    task = Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug="speaking-with-ai",
        title="Speaking",
        task_type="EXERCISE",
        description="",
    )

    apply_existing_learnpack_telemetry(task)
    task.refresh_from_db()

    assert task.telemetry_id == telemetry.id
    assert task.task_status == Task.TaskStatus.PENDING
    assert task.revision_status == Task.RevisionStatus.PENDING


@pytest.mark.django_db
def test_does_not_change_lessons(database):
    model = database.create(user=1, cohort=1)
    AssignmentTelemetry.objects.create(
        user=model.user,
        asset_slug="a-lesson",
        completion_rate=100,
        telemetry={},
    )
    task = Task.objects.create(
        user=model.user,
        cohort=model.cohort,
        associated_slug="a-lesson",
        title="A lesson",
        task_type="LESSON",
        description="",
    )

    apply_existing_learnpack_telemetry(task)
    task.refresh_from_db()

    assert task.telemetry_id is None
    assert task.task_status == Task.TaskStatus.PENDING
