"""
Test cases for delayed_revoke_discord_permissions task
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.models import CredentialsDiscord
from breathecode.authenticate.tasks import delayed_revoke_discord_permissions
from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.tests.mixins.breathecode_mixin import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    """Setup common mocks for all tests"""
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.revoke_user_discord_permissions", MagicMock())
    monkeypatch.setattr("breathecode.payments.actions.user_has_active_4geeks_plus_plans", MagicMock(return_value=False))
    yield


def test_delayed_revoke_discord_permissions_plan_financing_not_found():
    """Test when plan financing is not found"""
    with (
        patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke,
        pytest.raises(AbortTask) as exc_info,
    ):
        delayed_revoke_discord_permissions(
            entity_id=999, entity_type="plan_financing", date_field="valid_until"  # Non-existent ID
        )

    assert "plan_financing with id 999 not found" in str(exc_info.value)
    # Verify revoke was NOT called when entity not found
    assert not mock_revoke.called


def test_delayed_revoke_discord_permissions_subscription_not_expired(bc: Breathecode):
    """Test when subscription date has not expired yet"""
    model = bc.database.create(
        subscription={
            "status": "DEPRECATED",
            "valid_until": timezone.now() + timedelta(hours=1),  # Still future
        },
        user=1,
        academy=1,
    )

    with (
        patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke,
        pytest.raises(AbortTask) as exc_info,
    ):
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

    assert "has not expired yet" in str(exc_info.value)
    # Verify revoke was NOT called when date not expired
    assert not mock_revoke.called


def test_delayed_revoke_discord_permissions_subscription_active_status(bc: Breathecode):
    """Test when subscription is ACTIVE - should skip revocation"""
    model = bc.database.create(
        subscription={
            "status": "ACTIVE",  # Not a revokable status
            "valid_until": timezone.now() - timedelta(hours=1),  # Expired
        },
        user=1,
        academy=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    with patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke:
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

        # Should not revoke because status is ACTIVE
        assert not mock_revoke.called


def test_delayed_revoke_discord_permissions_user_has_other_active_plans(bc: Breathecode):
    """Test when user has other active 4Geeks Plus plans - should skip revocation"""
    model = bc.database.create(
        subscription={
            "status": "DEPRECATED",
            "valid_until": timezone.now() - timedelta(hours=1),  # Expired
        },
        user=1,
        academy=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    with (
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans", return_value=True),
        patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke,
    ):
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

        # Should not revoke because user has other active plans
        assert not mock_revoke.called


def test_delayed_revoke_discord_permissions_no_discord_credentials(bc: Breathecode):
    """Test when user has no Discord credentials - should abort task"""
    model = bc.database.create(
        subscription={
            "status": "DEPRECATED",
            "valid_until": timezone.now() - timedelta(hours=1),  # Expired
        },
        user=1,
        academy=1,
        # No Discord credentials created
    )

    with (
        patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke,
        pytest.raises(AbortTask) as exc_info,
    ):
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

    assert f"User {model.user.id} has no Discord credentials" in str(exc_info.value)
    # Verify revoke was NOT called when no Discord credentials
    assert not mock_revoke.called


@pytest.mark.parametrize("status", ["CANCELLED", "DEPRECATED", "PAYMENT_ISSUE", "EXPIRED", "ERROR"])
def test_delayed_revoke_discord_permissions_revokable_statuses(bc: Breathecode, status):
    """Test that all revokable statuses trigger revocation"""
    model = bc.database.create(
        subscription={
            "status": status,
            "valid_until": timezone.now() - timedelta(hours=1),  # Expired
        },
        user=1,
        academy=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    with patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke:
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

        # Should revoke for all these statuses
        mock_revoke.assert_called_once_with(model.user, model.academy)


@pytest.mark.parametrize("status", ["FREE_TRIAL", "ACTIVE"])
def test_delayed_revoke_discord_permissions_non_revokable_statuses(bc: Breathecode, status):
    """Test that non-revokable statuses skip revocation"""
    model = bc.database.create(
        subscription={
            "status": status,
            "valid_until": timezone.now() - timedelta(hours=1),  # Expired
        },
        user=1,
        academy=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    with patch("breathecode.authenticate.tasks.revoke_user_discord_permissions") as mock_revoke:
        delayed_revoke_discord_permissions(
            entity_id=model.subscription.id, entity_type="subscription", date_field="valid_until"
        )

        # Should NOT revoke for these statuses
        assert not mock_revoke.called
