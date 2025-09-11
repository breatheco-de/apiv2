"""
Test cases for delayed_revoke_discord_permissions
"""

import logging
from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.tasks import delayed_revoke_discord_permissions


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


# Disable fixtures for specific tests that need different mock setups
def pytest_collection_modifyitems(config, items):
    """Modify test items to disable fixtures for specific tests"""
    for item in items:
        if item.name in [
            "test_delayed_revoke_discord_permissions_subscription_not_found",
            "test_delayed_revoke_discord_permissions_plan_financing_not_found",
            "test_delayed_revoke_discord_permissions_date_not_expired",
        ]:
            # Remove fixtures that might interfere
            item.fixturenames = [
                f
                for f in item.fixturenames
                if f
                not in [
                    "mock_subscription",
                    "mock_plan_financing",
                    "mock_cohort",
                    "mock_credentials_discord",
                    "mock_revoke_permissions",
                ]
            ]


@pytest.fixture
def mock_subscription():
    """Mock Subscription model"""
    with patch("breathecode.authenticate.tasks.Subscription") as mock_sub:
        mock_instance = MagicMock()
        mock_sub.objects.filter.return_value.first.return_value = mock_instance
        mock_instance.status = "CANCELLED"
        mock_instance.user = MagicMock()
        mock_instance.academy = MagicMock()
        yield mock_instance


@pytest.fixture
def mock_plan_financing():
    """Mock PlanFinancing model"""
    with patch("breathecode.authenticate.tasks.PlanFinancing") as mock_pf:
        mock_instance = MagicMock()
        mock_pf.objects.filter.return_value.first.return_value = mock_instance
        mock_instance.status = "CANCELLED"
        mock_instance.user = MagicMock()
        mock_instance.academy = MagicMock()
        yield mock_instance


@pytest.fixture
def mock_cohort():
    """Mock Cohort model"""
    with patch("breathecode.authenticate.tasks.Cohort") as mock_cohort:
        mock_instance = MagicMock()
        mock_cohort.objects.filter.return_value.prefetch_related.return_value.first.return_value = mock_instance
        mock_instance.shortcuts = [{"label": "Discord", "server_id": "123456789", "role_id": "987654321"}]
        yield mock_instance


@pytest.fixture
def mock_credentials_discord():
    """Mock CredentialsDiscord model"""
    with patch("breathecode.authenticate.tasks.CredentialsDiscord") as mock_cd:
        mock_instance = MagicMock()
        mock_cd.objects.filter.return_value.first.return_value = mock_instance
        mock_instance.discord_id = "123456789"
        yield mock_instance


@pytest.fixture
def mock_revoke_permissions():
    """Mock revoke_user_discord_permissions function"""
    with patch("breathecode.payments.actions.revoke_user_discord_permissions") as mock_revoke:
        yield mock_revoke


def test_delayed_revoke_discord_permissions_subscription_not_found():
    """Test when subscription is not found"""
    # Don't use fixtures for this test as we need a different mock setup
    with (
        patch("breathecode.authenticate.tasks.Subscription") as mock_sub,
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
    ):

        # Mock the filter chain to return None
        mock_filter = MagicMock()
        mock_sub.objects.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Mock timezone.now() to avoid issues
        mock_tz.now.return_value = MagicMock()

        with pytest.raises(AbortTask) as exc_info:
            delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        assert "subscription with id 1 not found" in str(exc_info.value)


def test_delayed_revoke_discord_permissions_plan_financing_not_found():
    """Test when plan financing is not found"""
    # Don't use fixtures for this test as we need a different mock setup
    with (
        patch("breathecode.authenticate.tasks.PlanFinancing") as mock_pf,
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
    ):

        # Mock the filter chain to return None
        mock_filter = MagicMock()
        mock_pf.objects.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Mock timezone.now() to avoid issues
        mock_tz.now.return_value = MagicMock()

        with pytest.raises(AbortTask) as exc_info:
            delayed_revoke_discord_permissions(entity_id=1, entity_type="plan_financing", date_field="valid_until")

        assert "plan_financing with id 1 not found" in str(exc_info.value)


def test_delayed_revoke_discord_permissions_date_not_expired():
    """Test when target date has not expired yet"""
    # Don't use fixtures for this test as we need a different mock setup
    with (
        patch("breathecode.authenticate.tasks.Subscription") as mock_sub,
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
    ):

        # Create a mock subscription instance
        mock_instance = MagicMock()
        mock_instance.status = "CANCELLED"
        mock_instance.user = MagicMock()
        mock_instance.academy = MagicMock()

        # Mock the filter chain to return the instance
        mock_filter = MagicMock()
        mock_sub.objects.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_instance

        # Mock timezone.now()
        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be greater than now (not expired)
        future_date = MagicMock()
        future_date.__gt__ = MagicMock(return_value=True)  # Date is in the future
        mock_instance.valid_until = future_date

        with pytest.raises(AbortTask) as exc_info:
            delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        assert "has not expired yet" in str(exc_info.value)


def test_delayed_revoke_discord_permissions_invalid_status(mock_subscription):
    """Test when entity status is not in the allowed statuses"""
    mock_subscription.status = "ACTIVE"  # Not in allowed statuses

    with patch("breathecode.authenticate.tasks.timezone") as mock_tz:
        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be less than now (expired)
        mock_subscription.valid_until = MagicMock()
        mock_subscription.valid_until.__gt__ = MagicMock(return_value=False)

        # Should not raise exception, just return early
        result = delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        assert result is None


def test_delayed_revoke_discord_permissions_user_has_active_plans(
    mock_subscription, mock_cohort, mock_credentials_discord
):
    """Test when user has active 4Geeks Plus plans"""
    with (
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_active,
    ):

        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be less than now (expired)
        mock_subscription.valid_until = MagicMock()
        mock_subscription.valid_until.__gt__ = MagicMock(return_value=False)

        mock_has_active.return_value = True  # User has active plans

        # Should not raise exception, just return early
        result = delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        assert result is None


def test_delayed_revoke_discord_permissions_no_discord_credentials(mock_subscription, mock_cohort):
    """Test when user has no Discord credentials"""
    with (
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_active,
        patch("breathecode.authenticate.tasks.CredentialsDiscord") as mock_cd,
    ):

        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be less than now (expired)
        mock_subscription.valid_until = MagicMock()
        mock_subscription.valid_until.__gt__ = MagicMock(return_value=False)

        mock_has_active.return_value = False  # User has no active plans
        mock_cd.objects.filter.return_value.first.return_value = None  # No Discord credentials

        # Should not raise exception, just return early
        result = delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        assert result is None


def test_delayed_revoke_discord_permissions_successful_revoke(
    mock_subscription, mock_cohort, mock_credentials_discord, mock_revoke_permissions
):
    """Test successful Discord permissions revoke"""
    with (
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_active,
    ):

        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be less than now (expired)
        mock_subscription.valid_until = MagicMock()
        mock_subscription.valid_until.__gt__ = MagicMock(return_value=False)

        mock_has_active.return_value = False  # User has no active plans

        result = delayed_revoke_discord_permissions(entity_id=1, entity_type="subscription", date_field="valid_until")

        # Should call revoke_user_discord_permissions
        mock_revoke_permissions.assert_called_once_with(mock_subscription.user, mock_subscription.academy)


def test_delayed_revoke_discord_permissions_plan_financing_success(
    mock_plan_financing, mock_cohort, mock_credentials_discord, mock_revoke_permissions
):
    """Test successful Discord permissions revoke for plan financing"""
    with (
        patch("breathecode.authenticate.tasks.timezone") as mock_tz,
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_active,
    ):

        mock_now = MagicMock()
        mock_tz.now.return_value = mock_now

        # Mock the target_date to be less than now (expired)
        mock_plan_financing.valid_until = MagicMock()
        mock_plan_financing.valid_until.__gt__ = MagicMock(return_value=False)

        mock_has_active.return_value = False  # User has no active plans

        result = delayed_revoke_discord_permissions(entity_id=1, entity_type="plan_financing", date_field="valid_until")

        # Should call revoke_user_discord_permissions
        mock_revoke_permissions.assert_called_once_with(mock_plan_financing.user, mock_plan_financing.academy)
