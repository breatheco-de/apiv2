"""
Unit tests for tasks.process_auto_recharge (Celery task entrypoint).

Mock-based tests (no DB) verifying:
- Happy path: loads consumable and delegates to actions.process_auto_recharge.
- Not found path: raises AbortTask when consumable does not exist.

We bypass the Celery task decorator by temporarily replacing it with a no-op and reloading the module.
"""

import importlib
import sys
import pytest
from types import SimpleNamespace

from task_manager.core.exceptions import AbortTask


def _load_tasks_with_noop_decorator(monkeypatch):
    # Replace the task decorator with a pass-through factory before importing
    def noop_task_decorator(**kwargs):
        def _wrap(func):
            return func

        return _wrap

    monkeypatch.setattr("task_manager.django.decorators.task", noop_task_decorator, raising=False)

    # Reload the module to apply the patched decorator
    if "breathecode.payments.tasks" in sys.modules:
        del sys.modules["breathecode.payments.tasks"]
    return importlib.import_module("breathecode.payments.tasks")


def test_process_auto_recharge_calls_action(monkeypatch):
    """The task should fetch the consumable and call the action with it."""
    tasks = _load_tasks_with_noop_decorator(monkeypatch)

    fake_consumable = object()

    class DummyManager:
        def select_related(self, *_):
            return self

        def get(self, id):
            assert id == 123
            return fake_consumable

    monkeypatch.setattr(tasks, "Consumable", SimpleNamespace(objects=DummyManager()))

    called = {"consumable": None}

    def fake_action(consumable):
        called["consumable"] = consumable

    # Patch the action in the reloaded tasks module namespace
    monkeypatch.setattr(tasks.actions, "process_auto_recharge", fake_action)

    tasks.process_auto_recharge(123)
    assert called["consumable"] is fake_consumable


def test_process_auto_recharge_not_found(monkeypatch):
    """If the consumable does not exist, the task raises AbortTask."""
    tasks = _load_tasks_with_noop_decorator(monkeypatch)

    class DummyManager:
        def select_related(self, *_):
            return self

        def get(self, id):
            raise tasks.Consumable.DoesNotExist

    class DummyConsumable:
        class DoesNotExist(Exception):
            pass

    monkeypatch.setattr(
        tasks, "Consumable", SimpleNamespace(objects=DummyManager(), DoesNotExist=DummyConsumable.DoesNotExist)
    )

    with pytest.raises(AbortTask):
        tasks.process_auto_recharge(777)
