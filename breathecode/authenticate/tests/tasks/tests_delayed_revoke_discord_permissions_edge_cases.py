"""
Test cases for delayed_revoke_discord_permissions - Edge cases
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


def test_delayed_revoke_discord_permissions_subscription_not_found():
    """Test when subscription is not found"""
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
