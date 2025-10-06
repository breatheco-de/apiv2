import pytest
from types import SimpleNamespace

from task_manager.core.exceptions import RetryTask

from breathecode.payments import actions


class AttrDict(dict):
    """Dict that also allows attribute-style access for tests."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        self[name] = value


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def build_resource(owner_email="owner@example.com"):
    return SimpleNamespace(
        user=SimpleNamespace(email=owner_email),
        academy=SimpleNamespace(main_currency=SimpleNamespace(code="USD")),
        recharge_threshold_amount=50.0,
        max_period_spend=None,
        recharge_amount=25.0,
        __class__=SimpleNamespace(__name__="Subscription"),
        id=1,
        get_current_period_spend=lambda service, user=None: 0.0,
    )


def build_consumable(resource, seat_user=None, team_strategy=None, is_team_allowed=True):
    service = SimpleNamespace(is_team_allowed=is_team_allowed)
    service_item = SimpleNamespace(service=service)

    team = SimpleNamespace(consumption_strategy=team_strategy) if team_strategy else None
    seat = SimpleNamespace(user=seat_user, billing_team=team) if seat_user is not None else None

    return SimpleNamespace(
        id=99,
        subscription=resource,
        plan_financing=None,
        subscription_billing_team=team,
        subscription_seat=seat,
        service_item=service_item,
    )


# -----------------------------------------------------------------------------
# actions.process_auto_recharge: success path
# -----------------------------------------------------------------------------


def test_action_process_auto_recharge_success(monkeypatch):
    resource = build_resource()
    c = build_consumable(resource)

    # Lock OK
    class DummyLock:
        def __init__(self):
            self.released = False

        def acquire(self, blocking=False):
            return True

        def release(self):
            self.released = True

    class DummyRedis:
        def lock(self, *_, **__):
            return DummyLock()

    monkeypatch.setattr(actions.redis, "Redis", SimpleNamespace(from_url=lambda *_: DummyRedis()))

    # Validation returns price and amount
    monkeypatch.setattr(actions, "validate_auto_recharge_service_units", lambda instance: (10.0, 3, None))
    # Ensure charged_user has an email for description and notifications
    monkeypatch.setattr(actions, "get_user_from_consumable_to_be_charged", lambda instance: resource.user)

    # Replace Bag.objects.create to capture arguments
    created = AttrDict()

    class DummyBagManager:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch.setattr(actions, "Bag", SimpleNamespace(objects=DummyBagManager()))

    # Make transaction.atomic a no-op context manager
    class _Atomic:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(actions.transaction, "atomic", lambda: _Atomic())

    # Stripe.pay capture and call count
    paid = AttrDict()
    paid["calls"] = 0

    class DummyStripe:
        def __init__(self, academy):
            paid["academy"] = academy

        def pay(self, user, bag, amount, currency, description, subscription_billing_team=None, subscription_seat=None):
            paid["calls"] = paid.get("calls", 0) + 1
            paid.update(
                {
                    "user": user,
                    "bag": bag,
                    "amount": amount,
                    "currency": currency,
                    "description": description,
                    "team": subscription_billing_team,
                    "seat": subscription_seat,
                }
            )

    # Patch the real Stripe import path used inside the action
    monkeypatch.setattr("breathecode.payments.services.stripe.Stripe", DummyStripe, raising=False)

    # Emails capture
    sent = []

    def fake_send(template, email, context, academy=None):
        sent.append(AttrDict(template=template, email=email, context=context, academy=academy))

    monkeypatch.setattr(actions.notify_actions, "send_email_message", fake_send)

    # get_user_settings and translation
    monkeypatch.setattr(actions, "get_user_settings", lambda user: SimpleNamespace(lang="en"))
    monkeypatch.setattr(actions, "translation", lambda lang, en=None, es=None: en)

    actions.process_auto_recharge(c)

    # Bag created correctly
    assert created["user"] is resource.user
    assert created["academy"] is resource.academy
    assert created["currency"].code == "USD"
    assert created["type"] == "CHARGE"
    assert created["status"] == "PAID"
    assert created["was_delivered"] is True

    # Stripe called with aggregated amount
    assert paid["amount"] == 30.0
    assert paid["currency"] == "USD"
    assert paid["calls"] == 1

    # Emails sent to owner (and charged user == owner here by default)
    assert len(sent) >= 1
    assert sent[0]["template"] == "message"
    assert sent[0]["academy"] is resource.academy


# -----------------------------------------------------------------------------
# actions.process_auto_recharge: lock conflict path
# -----------------------------------------------------------------------------


def test_action_process_auto_recharge_lock_conflict(monkeypatch):
    resource = build_resource()
    c = build_consumable(resource)

    # Fake redis lock returns acquire False
    class DummyLock:
        def acquire(self, blocking=False):
            return False

        def release(self):
            pass

    class DummyRedis:
        def lock(self, *_, **__):
            return DummyLock()

    monkeypatch.setattr(actions.redis, "Redis", SimpleNamespace(from_url=lambda *_: DummyRedis()))
    monkeypatch.setattr(actions, "validate_auto_recharge_service_units", lambda instance: (10.0, 2, None))

    with pytest.raises(RetryTask):
        actions.process_auto_recharge(c)
