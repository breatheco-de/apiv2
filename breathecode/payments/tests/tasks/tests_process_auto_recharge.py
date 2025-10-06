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
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from breathecode.payments.models import Currency, Service, ServiceItem, Subscription, Consumable
from breathecode.admissions.models import Academy, Country, City
from breathecode.payments import tasks as tasks_mod

from task_manager.core.exceptions import AbortTask


def _call_underlying(func, *args, **kwargs):
    target = getattr(func, "__wrapped__", func)
    return target(*args, **kwargs)


def test_process_auto_recharge_calls_action(monkeypatch):
    """The task should fetch the consumable and call the action with it."""
    tasks = tasks_mod

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

    _call_underlying(tasks.process_auto_recharge, 123)
    assert called["consumable"] is fake_consumable


def test_process_auto_recharge_not_found(monkeypatch):
    """If the consumable does not exist, the task raises AbortTask."""
    tasks = tasks_mod

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
        _call_underlying(tasks.process_auto_recharge, 777)


def test_process_auto_recharge_db_happy_path(database, monkeypatch):
    """DB integration: creates real Consumable and ensures the task loads it and calls the action."""
    tasks = tasks_mod

    # Fixtures
    usd = Currency.objects.create(code="USD", name="US Dollar", decimals=2)
    owner = User.objects.create(username="owner", email="owner@example.com")
    country = Country.objects.create(code="US", name="United States")
    city = City.objects.create(name="City", country=country)

    academy = Academy.objects.create(
        slug="a1",
        name="Academy 1",
        logo_url="https://example.com/logo.png",
        street_address="Addr 1",
        city=city,
        country=country,
        main_currency=usd,
    )

    svc = Service.objects.create(slug="svc-1", owner=academy)
    si = ServiceItem.objects.create(service=svc, is_team_allowed=False)

    now = timezone.now()
    sub = Subscription.objects.create(
        user=owner,
        academy=academy,
        paid_at=now - relativedelta(days=1),
        next_payment_at=now + relativedelta(days=29),
    )

    c = Consumable.objects.create(service_item=si, user=owner, subscription=sub)

    called = {"consumable": None}

    def fake_action(consumable):
        called["consumable"] = consumable

    monkeypatch.setattr(tasks.actions, "process_auto_recharge", fake_action)

    _call_underlying(tasks.process_auto_recharge, c.id)
    assert called["consumable"].id == c.id
