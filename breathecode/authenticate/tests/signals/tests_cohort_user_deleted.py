from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, enable_signals):
    enable_signals("breathecode.authenticate.signals.cohort_user_deleted", "django.db.models.signals.pre_delete")
    yield


def test_same_call_two_times(bc: Breathecode, set_datetime):
    delta = timedelta(days=21)
    now = timezone.now()
    set_datetime(now)

    model = bc.database.create(cohort_user=2)

    for x in model.cohort_user:
        x.delete()

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                    1,
                ],
                "kwargs": {
                    "force": True,
                },
            },
            "duration": delta,
            "eta": now + delta,
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "async_remove_from_organization",
        },
    ]


def test_different_calls(bc: Breathecode, set_datetime):
    delta = timedelta(days=21)
    now = timezone.now()
    set_datetime(now)

    model = bc.database.create(cohort_user=[{"user_id": n + 1} for n in range(2)], user=2)

    for x in model.cohort_user:
        x.delete()

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                    1,
                ],
                "kwargs": {
                    "force": True,
                },
            },
            "duration": delta,
            "eta": now + delta,
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "async_remove_from_organization",
        },
        {
            "arguments": {
                "args": [
                    1,
                    2,
                ],
                "kwargs": {
                    "force": True,
                },
            },
            "duration": delta,
            "eta": now + delta,
            "id": 2,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "async_remove_from_organization",
        },
    ]
