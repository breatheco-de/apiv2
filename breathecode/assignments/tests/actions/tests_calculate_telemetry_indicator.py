from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from breathecode.assignments.actions import calculate_telemetry_indicator
from breathecode.assignments.models import Task

# 2024-01-15T10:00:00 UTC in milliseconds
OPENED_AT_MS = 1705312800000
# 2024-01-15T11:30:00 UTC in milliseconds
COMPLETED_AT_MS = 1705318200000


def _partial_telemetry_payload():
    """Two steps, only one completed → completion_rate 50%."""
    return {
        "last_interaction_at": COMPLETED_AT_MS,
        "tutorial_started_at": OPENED_AT_MS,
        "workout_session": [{}],
        "steps": [
            {
                "slug": "step-1",
                "opened_at": OPENED_AT_MS,
                "completed_at": COMPLETED_AT_MS,
            },
            {
                "slug": "step-2",
                "opened_at": OPENED_AT_MS,
                "completed_at": None,
            },
        ],
    }


def _make_telemetry(payload):
    telemetry = MagicMock()
    telemetry.asset_slug = "exercise-anti-downgrade"
    telemetry.user = MagicMock()
    telemetry.telemetry = payload
    return telemetry


def _graded_asset():
    asset = MagicMock()
    asset.graded = True
    return asset


@patch("breathecode.assignments.actions.Asset")
def test_does_not_downgrade_done_exercise_when_completion_rate_is_low(Asset):
    Asset.objects.filter.return_value.first.return_value = _graded_asset()

    delivered_at = datetime(2024, 1, 15, 12, 0, tzinfo=dt_timezone.utc)
    task = MagicMock()
    task.task_type = Task.TaskType.EXERCISE
    task.task_status = Task.TaskStatus.DONE
    task.revision_status = Task.RevisionStatus.APPROVED
    task.description = "You have completed all steps on this exercise"
    task.delivered_at = delivered_at

    telemetry = _make_telemetry(_partial_telemetry_payload())

    calculate_telemetry_indicator(telemetry, asset_tasks=[task])

    assert telemetry.completion_rate < 99.999
    task.save.assert_not_called()
    assert task.task_status == Task.TaskStatus.DONE
    assert task.revision_status == Task.RevisionStatus.APPROVED
    assert task.description == "You have completed all steps on this exercise"
    assert task.delivered_at == delivered_at


@patch("breathecode.assignments.actions.Asset")
def test_pending_exercise_is_kept_pending_when_completion_rate_is_low(Asset):
    Asset.objects.filter.return_value.first.return_value = _graded_asset()

    task = MagicMock()
    task.task_type = Task.TaskType.EXERCISE
    task.task_status = Task.TaskStatus.PENDING
    task.revision_status = Task.RevisionStatus.PENDING

    telemetry = _make_telemetry(_partial_telemetry_payload())

    calculate_telemetry_indicator(telemetry, asset_tasks=[task])

    assert telemetry.completion_rate < 99.999
    assert task.task_status == Task.TaskStatus.PENDING
    assert task.revision_status == Task.RevisionStatus.PENDING
    assert task.delivered_at is None
    task.save.assert_called_once()
