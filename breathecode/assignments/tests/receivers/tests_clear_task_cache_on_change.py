from unittest.mock import MagicMock, call

import pytest

from breathecode.assignments import receivers
from breathecode.assignments.caches import TaskCache
from breathecode.assignments.models import Task


@pytest.fixture(autouse=True)
def setup(db, monkeypatch, enable_signals):
    enable_signals("django.db.models.signals.post_save", "django.db.models.signals.post_delete")
    monkeypatch.setattr(TaskCache, "clear", MagicMock())
    monkeypatch.setattr(receivers, "is_cache_enabled", lambda: True)
    yield


def test_cache_is_not_cleared_before_commit(database):
    database.create(task=1)

    assert TaskCache.clear.call_args_list == []


def test_cache_is_cleared_on_save(database, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        model = database.create(task=1)

    TaskCache.clear.reset_mock()

    with django_capture_on_commit_callbacks(execute=True):
        model.task.description = "Feedback 2"
        model.task.save()

    assert TaskCache.clear.call_args_list == [call(max_deep=0)]


def test_cache_is_cleared_on_delete(database, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        database.create(task=1)

    TaskCache.clear.reset_mock()

    with django_capture_on_commit_callbacks(execute=True):
        Task.objects.all().delete()

    assert TaskCache.clear.call_args_list == [call(max_deep=0)]


def test_cache_is_not_cleared_when_disabled(database, django_capture_on_commit_callbacks, monkeypatch):
    monkeypatch.setattr(receivers, "is_cache_enabled", lambda: False)

    with django_capture_on_commit_callbacks(execute=True):
        database.create(task=1)

    assert TaskCache.clear.call_args_list == []


def test_cache_errors_do_not_break_the_save(database, django_capture_on_commit_callbacks):
    TaskCache.clear.side_effect = Exception("redis is down")

    with django_capture_on_commit_callbacks(execute=True):
        database.create(task=1)

    assert Task.objects.count() == 1
    assert TaskCache.clear.call_args_list == [call(max_deep=0)]
