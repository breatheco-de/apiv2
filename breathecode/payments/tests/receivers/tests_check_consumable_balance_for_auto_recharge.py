"""
Unit tests for receivers.check_consumable_balance_for_auto_recharge.

Mock-based tests (no DB). Verifies that:
- If validation returns an error -> task is not enqueued.
- If amount is 0 -> task is not enqueued.
- If amount > 0 and no error -> enqueues tasks.process_auto_recharge.delay with the consumable id.
"""

from types import SimpleNamespace
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from breathecode.payments import receivers, tasks
from breathecode.payments.models import Currency, Service, ServiceItem, Subscription, Consumable
from breathecode.admissions.models import Academy, Country, City


def build_consumable():
    """Build minimal consumable stub used by the receiver tests."""
    return SimpleNamespace(
        id=99,
        subscription=SimpleNamespace(__class__=SimpleNamespace(__name__="Subscription")),
        plan_financing=None,
    )


def test_check_consumable_balance_for_auto_recharge__error(monkeypatch):
    """When validation returns an error, do not enqueue the auto-recharge task."""
    c = build_consumable()

    monkeypatch.setattr(
        receivers,
        "validate_auto_recharge_service_units",
        lambda instance: (0.0, 0, "some-error"),
    )

    called = {"delay": False}

    def fake_delay(consumable_id):
        called["delay"] = True

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c)
    assert called["delay"] is False


def test_check_consumable_balance_for_auto_recharge__amount_zero(monkeypatch):
    """When validation returns amount=0, do not enqueue the auto-recharge task."""
    c = build_consumable()

    monkeypatch.setattr(receivers, "validate_auto_recharge_service_units", lambda instance: (10.0, 0, None))

    called = {"delay": False}

    def fake_delay(consumable_id):
        called["delay"] = True

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c)
    assert called["delay"] is False


def test_check_consumable_balance_for_auto_recharge__ok(monkeypatch):
    """When validation returns a positive amount and no error, enqueue the task with consumable id."""
    c = build_consumable()

    monkeypatch.setattr(receivers, "validate_auto_recharge_service_units", lambda instance: (10.0, 2, None))

    captured = {"consumable_id": None}

    def fake_delay(consumable_id):
        captured["consumable_id"] = consumable_id

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c)
    assert captured["consumable_id"] == c.id


def test_check_consumable_balance_for_auto_recharge__db_happy_path(database, monkeypatch):
    """DB integration: create real Consumable and ensure the task is enqueued with its id."""
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

    # Validation returns positive amount without error
    monkeypatch.setattr(receivers, "validate_auto_recharge_service_units", lambda instance: (10.0, 1, None))

    captured = {"consumable_id": None}

    def fake_delay(consumable_id):
        captured["consumable_id"] = consumable_id

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c)
    assert captured["consumable_id"] == c.id
