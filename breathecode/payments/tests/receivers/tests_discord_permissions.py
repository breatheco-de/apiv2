"""
Test receivers for Discord permissions in payments
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.authenticate import tasks as auth_tasks
from breathecode.authenticate.models import Cohort, CredentialsDiscord
from breathecode.payments.models import Plan, PlanFinancing, Subscription
from breathecode.payments.receivers import grant_discord_permissions_receiver, revoke_discord_permissions_receiver
from breathecode.payments.signals import grant_plan_permissions, revoke_plan_permissions
from breathecode.tests.mixins.breathecode_mixin import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch, enable_signals):
    """Setup common mocks for all tests"""
    enable_signals(
        "breathecode.payments.signals.revoke_plan_permissions",
        "breathecode.payments.signals.grant_plan_permissions",
    )

    mock_manager = MagicMock()
    mock_manager.exists.return_value = False
    mock_manager.call.return_value = None

    mock_revoke = MagicMock()

    monkeypatch.setattr(auth_tasks.delayed_revoke_discord_permissions, "delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.assign_discord_role_task.delay", MagicMock())
    monkeypatch.setattr("breathecode.payments.receivers.revoke_user_discord_permissions", mock_revoke)
    monkeypatch.setattr("breathecode.payments.actions.user_has_active_4geeks_plus_plans", MagicMock(return_value=False))
    monkeypatch.setattr("breathecode.payments.receivers.schedule_task", MagicMock(return_value=mock_manager))

    yield {"manager": mock_manager, "revoke": mock_revoke}


def test_revoke_discord_permissions_receiver_with_subscription_cancelled_with_valid_until(bc: Breathecode, setup):
    """Test revoke_discord_permissions_receiver with cancelled subscription that has valid_until"""
    mock_manager = setup["manager"]

    # Create test data using bc mixin
    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    # Associate the plan with the subscription
    subscription = model.subscription
    subscription.plans.add(model.plan)

    # Set subscription as ACTIVE first, then change to DEPRECATED to trigger signal
    subscription.status = "ACTIVE"
    subscription.valid_until = timezone.now() + timedelta(days=30)
    subscription.save()

    # Now change to DEPRECATED to trigger the revoke signal - this should trigger the signal
    subscription.status = "CANCELLED"
    subscription.save()

    # Verify schedule_task was called with the correct parameters
    mock_manager.call.assert_called_once_with(subscription.id, "subscription", "valid_until")


def test_revoke_discord_permissions_receiver_user_has_active_4geeks_plus_plans(bc: Breathecode, setup):
    """Test receiver skips when user has other active 4Geeks Plus plans"""
    mock_manager = setup["manager"]
    mock_revoke = setup["revoke"]

    # Create test data
    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    # Mock user_has_active_4geeks_plus_plans to return True (user has other active plans)
    with patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans", return_value=True):
        subscription.status = "ACTIVE"
        subscription.valid_until = timezone.now() + timedelta(days=30)
        subscription.save()

        subscription.status = "DEPRECATED"
        subscription.save()

        # Verify schedule_task was NOT called because user has other active plans
        assert not mock_manager.call.called

        # Verify revoke_user_discord_permissions was also NOT called (user has other active plans)
        assert not mock_revoke.called


def test_revoke_discord_permissions_receiver_with_cancelled_status_and_both_dates_future(bc: Breathecode, setup):
    """Test receiver with CANCELLED status and both valid_until and next_payment_at in the future"""
    mock_manager = setup["manager"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    # Set both dates in the future - valid_until is closer (15 days), next_payment_at is further (30 days)
    subscription.valid_until = timezone.now() + timedelta(days=15)
    subscription.next_payment_at = timezone.now() + timedelta(days=30)
    subscription.save()

    # Change to CANCELLED status
    subscription.status = "CANCELLED"
    subscription.save()

    # Verify schedule_task was called with valid_until (should take precedence over next_payment_at)
    mock_manager.call.assert_called_once_with(subscription.id, "subscription", "valid_until")


def test_revoke_discord_permissions_receiver_with_cancelled_status_and_next_payment_at_future(bc: Breathecode, setup):
    """Test receiver with CANCELLED status and next_payment_at in the future"""
    mock_manager = setup["manager"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.next_payment_at = timezone.now() + timedelta(days=15)
    subscription.valid_until = None  # No valid_until, should check next_payment_at
    subscription.save()

    subscription.status = "CANCELLED"
    subscription.save()

    # Verify schedule_task was called with next_payment_at
    mock_manager.call.assert_called_once_with(subscription.id, "subscription", "next_payment_at")


def test_revoke_discord_permissions_receiver_with_cancelled_status_and_expired_valid_until(bc: Breathecode, setup):
    """Test receiver with CANCELLED status and expired valid_until - should revoke immediately"""
    mock_manager = setup["manager"]
    mock_revoke = setup["revoke"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.valid_until = timezone.now() - timedelta(days=1)  # Expired
    subscription.save()

    subscription.status = "CANCELLED"
    subscription.save()

    # Verify schedule_task was NOT called (should revoke immediately)
    assert not mock_manager.call.called

    # Verify revoke_user_discord_permissions was called immediately
    mock_revoke.assert_called_once_with(subscription.user, subscription.academy)


def test_revoke_discord_permissions_receiver_with_deprecated_status_and_expired_valid_until(bc: Breathecode, setup):
    """Test receiver with DEPRECATED status and expired valid_until - should revoke immediately"""
    mock_manager = setup["manager"]
    mock_revoke = setup["revoke"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.valid_until = timezone.now() - timedelta(days=1)  # Expired
    subscription.save()

    subscription.status = "DEPRECATED"
    subscription.save()

    # Verify schedule_task was NOT called (should revoke immediately)
    assert not mock_manager.call.called

    # Verify revoke_user_discord_permissions was called immediately
    mock_revoke.assert_called_once_with(subscription.user, subscription.academy)


def test_revoke_discord_permissions_receiver_with_deprecated_status_and_no_valid_until(bc: Breathecode, setup):
    """Test receiver with DEPRECATED status and no valid_until - should revoke immediately"""
    mock_manager = setup["manager"]
    mock_revoke = setup["revoke"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.valid_until = None
    subscription.save()

    subscription.status = "DEPRECATED"
    subscription.save()

    # Verify schedule_task was NOT called (should revoke immediately)
    assert not mock_manager.call.called

    # Verify revoke_user_discord_permissions was called immediately
    mock_revoke.assert_called_once_with(subscription.user, subscription.academy)


def test_revoke_discord_permissions_receiver_with_non_4geeks_plus_plan(bc: Breathecode, setup):
    """Test receiver with a plan that is not 4geeks-plus - should not do anything"""
    mock_manager = setup["manager"]
    mock_revoke = setup["revoke"]

    model = bc.database.create(
        subscription=1,
        plan={"slug": "regular-plan", "is_renewable": False},  # Different plan
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.valid_until = timezone.now() + timedelta(days=30)
    subscription.save()

    subscription.status = "DEPRECATED"
    subscription.save()

    # Verify schedule_task was NOT called (not a 4geeks-plus plan)
    assert not mock_manager.call.called

    # Verify revoke_user_discord_permissions was also NOT called (not a 4geeks-plus plan)
    assert not mock_revoke.called


def test_revoke_discord_permissions_receiver_with_plan_financing(bc: Breathecode, setup):
    """Test receiver with PlanFinancing instead of Subscription"""
    mock_manager = setup["manager"]

    model = bc.database.create(
        plan_financing={
            "monthly_price": 100,
            "plan_expires_at": timezone.now() + timedelta(days=365),
        },
        plan={"slug": "4geeks-plus-planfinancing", "is_renewable": False},
        academy=1,
        user=1,
    )

    plan_financing = model.plan_financing
    plan_financing.plans.add(model.plan)

    plan_financing.status = "ACTIVE"
    plan_financing.valid_until = timezone.now() + timedelta(days=30)
    plan_financing.save()

    plan_financing.status = "CANCELLED"
    plan_financing.save()

    # Verify schedule_task was called with plan_financing entity_type
    mock_manager.call.assert_called_once_with(plan_financing.id, "plan_financing", "valid_until")


def test_revoke_discord_permissions_receiver_manager_exists_returns_true(bc: Breathecode, setup):
    """Test receiver when manager.exists returns True - should not call manager.call"""
    mock_manager = setup["manager"]
    mock_manager.exists.return_value = True  # Task already exists

    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    subscription = model.subscription
    subscription.plans.add(model.plan)

    subscription.status = "ACTIVE"
    subscription.valid_until = timezone.now() + timedelta(days=30)
    subscription.save()

    subscription.status = "DEPRECATED"
    subscription.save()

    # Verify manager.exists was called but manager.call was NOT called
    mock_manager.exists.assert_called_once_with(subscription.id, "subscription", "valid_until")
    assert not mock_manager.call.called
