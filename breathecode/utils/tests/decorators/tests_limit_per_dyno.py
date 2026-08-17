import pytest
from redis.exceptions import LockError
from task_manager.core.exceptions import RetryTask

from breathecode.utils.decorators.task import acquire_dyno_slot, limit_per_dyno, release_dyno_slot, slots_per_dyno


class BusyLock:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        raise LockError("busy")

    def __exit__(self, *args):
        pass


class RecordingLock:
    entered = 0
    exited = 0

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        RecordingLock.entered += 1
        return self

    def __exit__(self, *args):
        RecordingLock.exited += 1


def test_slots_per_dyno_uses_requested_number(monkeypatch):
    monkeypatch.setenv("CELERY_MAX_WORKERS", "4")
    assert slots_per_dyno(2) == 2


def test_slots_per_dyno_caps_at_max_workers(monkeypatch):
    monkeypatch.setenv("CELERY_MAX_WORKERS", "1")
    assert slots_per_dyno(9) == 1


def test_slots_per_dyno_defaults_max_workers_to_two(monkeypatch):
    monkeypatch.delenv("CELERY_MAX_WORKERS", raising=False)
    assert slots_per_dyno(9) == 2


def test_acquire_dyno_slot_retries_when_full(monkeypatch):
    monkeypatch.setattr("breathecode.utils.decorators.task.Lock", BusyLock)
    monkeypatch.setenv("CELERY_MAX_WORKERS", "2")
    monkeypatch.setenv("DYNO", "celeryworker.1")

    with pytest.raises(RetryTask, match="Too many heavy_task running on this dyno"):
        acquire_dyno_slot("heavy_task", 2)


def test_limit_per_dyno_releases_slot(monkeypatch):
    RecordingLock.entered = 0
    RecordingLock.exited = 0
    monkeypatch.setattr("breathecode.utils.decorators.task.Lock", RecordingLock)
    monkeypatch.setenv("DYNO", "celeryworker.2")
    monkeypatch.setenv("CELERY_MAX_WORKERS", "2")

    @limit_per_dyno(2)
    def heavy():
        return "ok"

    assert heavy() == "ok"
    assert RecordingLock.entered == 1
    assert RecordingLock.exited == 1


def test_limit_per_dyno_releases_slot_on_error(monkeypatch):
    RecordingLock.entered = 0
    RecordingLock.exited = 0
    monkeypatch.setattr("breathecode.utils.decorators.task.Lock", RecordingLock)
    monkeypatch.setenv("CELERY_MAX_WORKERS", "2")

    @limit_per_dyno(1, name="named_heavy")
    def heavy():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        heavy()

    assert RecordingLock.entered == 1
    assert RecordingLock.exited == 1


def test_release_dyno_slot_none():
    release_dyno_slot(None)
