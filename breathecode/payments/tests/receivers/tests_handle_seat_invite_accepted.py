import pytest
from unittest.mock import MagicMock

from django.utils import timezone
from breathecode.authenticate.models import UserInvite
from breathecode.authenticate.signals import invite_status_updated


@pytest.fixture(autouse=True)
def auto_enable_signals(enable_signals):
    enable_signals()
    yield


def _create_subscription_with_team(database):
    # minimal academy/currency to satisfy FKs (Academy requires city/country)
    model = database.create(country=1, city=1, academy=1, currency=1, subscription=1)
    subscription = model.subscription

    # create a billing team for this subscription
    team = database.create(
        subscription_billing_team={"subscription_id": subscription.id}, country=1, city=1
    ).subscription_billing_team

    return subscription, team


def test_invite_accept_binds_seat_and_triggers_scheduler(database, monkeypatch):
    subscription, team = _create_subscription_with_team(database)

    # pending seat by email
    seat = database.create(
        subscription_seat={
            "billing_team_id": team.id,
            "email": "Member@Example.com",
            "user": None,
            "is_active": True,
            "seat_multiplier": 1,
        }
    ).subscription_seat

    # invite accepted with same email (different case)
    user = database.create(user={"email": "member@example.com"}).user
    invite = database.create(user_invite={"email": user.email, "status": "ACCEPTED", "user_id": user.id}).user_invite

    called = MagicMock()
    # avoid external email validation side-effects on invite signal
    monkeypatch.setattr(
        "breathecode.authenticate.tasks.async_validate_email_invite",
        lambda *args, **kwargs: None,
    )

    class DummyTask:
        def delay(self, *args, **kwargs):
            called(*args, **kwargs)

    monkeypatch.setattr(
        "breathecode.payments.tasks.build_service_stock_scheduler_from_subscription",
        DummyTask(),
    )
    # also patch the tasks alias inside receivers
    import types

    receivers_tasks = types.SimpleNamespace(build_service_stock_scheduler_from_subscription=DummyTask())
    monkeypatch.setattr("breathecode.payments.receivers.tasks", receivers_tasks)

    # make plan consumption_strategy BOTH so per-seat path is enabled even if team has no strategy
    plan = database.create(
        plan={"owner_id": subscription.academy_id, "time_of_life": None, "time_of_life_unit": None}
    ).plan
    subscription.plans.add(plan)
    # attach attribute dynamically in runtime
    try:
        from breathecode.payments.models import Plan

        plan.consumption_strategy = Plan.ConsumptionStrategy.BOTH
    except Exception:
        plan.consumption_strategy = "BOTH"  # fallback if enum is not available in this environment

    invite_status_updated.send(sender=UserInvite, instance=invite)

    seat.refresh_from_db()

    assert seat.user_id == user.id
    assert seat.email == user.email

    # called with seat id
    called.assert_called_once_with(subscription.id, seat_id=seat.id)


def test_invite_accept_binds_seat_no_scheduler_when_not_per_seat(database, monkeypatch):
    subscription, team = _create_subscription_with_team(database)

    # pending seat by email
    seat = database.create(
        subscription_seat={
            "billing_team_id": team.id,
            "email": "member@example.com",
            "user": None,
            "is_active": True,
            "seat_multiplier": 1,
        }
    ).subscription_seat

    # invite accepted with same email
    user = database.create(user={"email": "member@example.com"}).user
    invite = database.create(user_invite={"email": user.email, "status": "ACCEPTED", "user_id": user.id}).user_invite

    called = MagicMock()
    # avoid external email validation side-effects on invite signal
    monkeypatch.setattr(
        "breathecode.authenticate.tasks.async_validate_email_invite",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("breathecode.payments.tasks.build_service_stock_scheduler_from_subscription.delay", called)

    # Set plan consumption strategy to PER_TEAM so per-seat path is disabled
    plan = database.create(
        plan={"owner_id": subscription.academy_id, "time_of_life": None, "time_of_life_unit": None}
    ).plan
    subscription.plans.add(plan)
    try:
        from breathecode.payments.models import Plan

        plan.consumption_strategy = Plan.ConsumptionStrategy.PER_TEAM
    except Exception:
        plan.consumption_strategy = "PER_TEAM"

    invite_status_updated.send(sender=UserInvite, instance=invite)

    seat.refresh_from_db()

    assert seat.user_id == user.id
    # current receiver always schedules per-seat consumables on invite acceptance
    called.assert_called_once_with(subscription.id, seat_id=seat.id)
