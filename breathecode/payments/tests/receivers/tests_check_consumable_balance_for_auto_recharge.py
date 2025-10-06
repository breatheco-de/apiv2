"""
Unit tests for receivers.check_consumable_balance_for_auto_recharge.

Mock-based tests (no DB). Verifies that:
- If validation returns an error -> task is not enqueued.
- If amount is 0 -> task is not enqueued.
- If amount > 0 and no error -> enqueues tasks.process_auto_recharge.delay with the consumable id.
"""

from types import SimpleNamespace

from breathecode.payments import actions, receivers, tasks


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

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c, how_many=1)
    assert called["delay"] is False


def test_check_consumable_balance_for_auto_recharge__amount_zero(monkeypatch):
    """When validation returns amount=0, do not enqueue the auto-recharge task."""
    c = build_consumable()

    monkeypatch.setattr(receivers, "validate_auto_recharge_service_units", lambda instance: (10.0, 0, None))

    called = {"delay": False}

    def fake_delay(consumable_id):
        called["delay"] = True

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c, how_many=1)
    assert called["delay"] is False


def test_check_consumable_balance_for_auto_recharge__ok(monkeypatch):
    """When validation returns a positive amount and no error, enqueue the task with consumable id."""
    c = build_consumable()

    monkeypatch.setattr(receivers, "validate_auto_recharge_service_units", lambda instance: (10.0, 2, None))

    captured = {"consumable_id": None}

    def fake_delay(consumable_id):
        captured["consumable_id"] = consumable_id

    monkeypatch.setattr(tasks.process_auto_recharge, "delay", fake_delay)

    receivers.check_consumable_balance_for_auto_recharge(sender=None, instance=c, how_many=1)
    assert captured["consumable_id"] == c.id
