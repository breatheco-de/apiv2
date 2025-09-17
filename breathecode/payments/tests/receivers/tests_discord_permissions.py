"""
Test receivers for Discord permissions in payments
"""

from unittest.mock import MagicMock, patch

import pytest

from breathecode.admissions.models import CohortUser
from breathecode.authenticate import tasks as auth_tasks
from breathecode.authenticate.models import Cohort, CredentialsDiscord
from breathecode.payments.models import Plan, PlanFinancing, Subscription
from breathecode.payments.receivers import grant_discord_permissions_receiver, revoke_discord_permissions_receiver
from breathecode.payments.signals import grant_plan_permissions, revoke_plan_permissions
from breathecode.tests.mixins.breathecode_mixin import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    """Setup common mocks for all tests"""
    monkeypatch.setattr(auth_tasks.delayed_revoke_discord_permissions, "delay", MagicMock())
    monkeypatch.setattr(auth_tasks.assign_discord_role_task, "delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.actions.revoke_user_discord_permissions", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.user_has_active_4geeks_plus_plans", MagicMock(return_value=False))
    monkeypatch.setattr("breathecode.payments.actions.user_has_active_paid_plans", MagicMock(return_value=False))
    monkeypatch.setattr("task_manager.django.actions.schedule_task", MagicMock())
    yield


def test_revoke_discord_permissions_receiver_with_subscription_cancelled_with_valid_until(bc: Breathecode):
    """Test revoke_discord_permissions_receiver with cancelled subscription that has valid_until"""
    from datetime import timedelta

    from django.utils import timezone

    # Create test data using bc mixin
    model = bc.database.create(
        subscription=1,
        plan={"slug": "4geeks-plus-subscription", "is_renewable": False},
        academy=1,
        user=1,
    )

    # Set subscription as cancelled with valid_until in the future
    subscription = model.subscription
    subscription.status = "CANCELLED"
    subscription.valid_until = timezone.now() + timedelta(days=30)
    subscription.save()

    # Mock the schedule_task to return a manager with exists method
    mock_manager = MagicMock()
    mock_manager.exists.return_value = False
    mock_manager.call.return_value = None

    with (
        patch("task_manager.django.actions.schedule_task", return_value=mock_manager),
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans", return_value=False),
    ):
        # Trigger the receiver
        revoke_plan_permissions.send_robust(sender=Subscription, instance=subscription)

        # Verify schedule_task was called
        mock_manager.call.assert_called_once_with(subscription.id, "subscription", "valid_until")
