import pytest

from unittest.mock import MagicMock, call
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.activity.management.commands.upload_activities import Command

UTC_NOW = timezone.now()


def get_calls():
    utc_now = timezone.now()

    for i in range(1, 11):
        cursor = utc_now + timezone.timedelta(minutes=i)
        yield call(args=(), eta=cursor)


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch):
    m1 = MagicMock()

    monkeypatch.setattr(
        "breathecode.activity.management.commands.upload_activities.get_activity_sampling_rate", lambda: 60
    )
    monkeypatch.setattr("breathecode.activity.tasks.upload_activities.apply_async", m1)
    monkeypatch.setattr("django.utils.timezone.now", lambda: UTC_NOW)

    yield m1


def test_schedule_all_executions(bc: Breathecode, apply_patch):
    upload_activities_mock = apply_patch

    command = Command()
    result = command.handle()

    assert result is None
    assert upload_activities_mock.call_args_list == [*get_calls()]
