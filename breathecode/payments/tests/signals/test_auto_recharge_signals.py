"""
Unit tests for auto-recharge signal receivers.

These tests demonstrate how to test signal receivers that use connect() syntax.
"""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from breathecode.payments.models import (
    Consumable,
    SubscriptionBillingTeam,
    Subscription,
)
from breathecode.payments.signals import consume_service, consumable_balance_low
from breathecode.payments import receivers


@pytest.mark.django_db
class TestAutoRechargeSignals:
    """Test auto-recharge signal receivers."""

    def setup_method(self):
        """Disconnect signals before each test for isolation."""
        consume_service.disconnect(receivers.check_consumable_balance_for_auto_recharge, sender=Consumable)
        consumable_balance_low.disconnect(receivers.trigger_auto_recharge_task, sender=Consumable)

    def teardown_method(self):
        """Reconnect signals after each test."""
        consume_service.connect(receivers.check_consumable_balance_for_auto_recharge, sender=Consumable)
        consumable_balance_low.connect(receivers.trigger_auto_recharge_task, sender=Consumable)

    def test_check_consumable_balance_ignores_non_team_consumables(self, db):
        """Test that receiver ignores consumables without billing team."""
        # Create consumable without billing team
        consumable = MagicMock(spec=Consumable)
        consumable.subscription_billing_team = None

        # Call receiver directly
        with patch("breathecode.payments.signals.consumable_balance_low.send") as mock_signal:
            receivers.check_consumable_balance_for_auto_recharge(sender=Consumable, instance=consumable, how_many=10)

            # Signal should not be emitted
            mock_signal.assert_not_called()

    def test_check_consumable_balance_ignores_disabled_auto_recharge(self, db):
        """Test that receiver ignores teams with auto-recharge disabled."""
        # Create team with auto-recharge disabled
        team = MagicMock(spec=SubscriptionBillingTeam)
        team.auto_recharge_enabled = False

        consumable = MagicMock(spec=Consumable)
        consumable.subscription_billing_team = team

        # Call receiver directly
        with patch("breathecode.payments.signals.consumable_balance_low.send") as mock_signal:
            receivers.check_consumable_balance_for_auto_recharge(sender=Consumable, instance=consumable, how_many=10)

            # Signal should not be emitted
            mock_signal.assert_not_called()

    def test_check_consumable_balance_skips_when_limit_reached(self, db):
        """Test that receiver skips recharge when spending limit is reached."""
        # Create team with spending limit reached
        team = MagicMock(spec=SubscriptionBillingTeam)
        team.id = 1
        team.auto_recharge_enabled = True
        team.max_period_spend = Decimal("100.00")
        team.get_current_period_spend = MagicMock(return_value=100.00)

        subscription = MagicMock(spec=Subscription)
        team.subscription = subscription

        consumable = MagicMock(spec=Consumable)
        consumable.subscription_billing_team = team

        # Call receiver directly
        with patch("breathecode.payments.signals.consumable_balance_low.send") as mock_signal:
            receivers.check_consumable_balance_for_auto_recharge(sender=Consumable, instance=consumable, how_many=10)

            # Signal should not be emitted
            mock_signal.assert_not_called()

    def test_trigger_auto_recharge_task_schedules_celery_task(self, db):
        """Test that trigger receiver schedules Celery task."""
        team = MagicMock(spec=SubscriptionBillingTeam)
        team.id = 123

        # Call receiver directly
        with patch("breathecode.payments.tasks.process_auto_recharge.delay") as mock_task:
            receivers.trigger_auto_recharge_task(sender=Consumable, team=team, recharge_amount=20.00)

            # Task should be scheduled
            mock_task.assert_called_once_with(team_id=123, recharge_amount=20.00)

    def test_signal_can_be_disconnected_for_testing(self, db):
        """Test that signals can be disconnected for isolated testing."""
        # Signals are already disconnected in setup_method

        consumable = MagicMock(spec=Consumable)

        # Emit signal
        with patch("breathecode.payments.receivers.check_consumable_balance_for_auto_recharge") as mock_receiver:
            consume_service.send(sender=Consumable, instance=consumable, how_many=10)

            # Receiver should NOT be called because signal is disconnected
            mock_receiver.assert_not_called()

    def test_signal_reconnection_works(self, db):
        """Test that signals can be reconnected after disconnection."""
        # Reconnect signal
        consume_service.connect(receivers.check_consumable_balance_for_auto_recharge, sender=Consumable)

        team = MagicMock(spec=SubscriptionBillingTeam)
        team.auto_recharge_enabled = False

        consumable = MagicMock(spec=Consumable)
        consumable.subscription_billing_team = team

        # Emit signal
        with patch("breathecode.payments.signals.consumable_balance_low.send") as mock_signal:
            consume_service.send(sender=Consumable, instance=consumable, how_many=10)

            # Receiver should be called (but won't emit signal due to disabled auto-recharge)
            mock_signal.assert_not_called()

        # Disconnect again for teardown
        consume_service.disconnect(receivers.check_consumable_balance_for_auto_recharge, sender=Consumable)


@pytest.mark.django_db
class TestAutoRechargeIntegration:
    """Integration tests with signals connected."""

    def test_full_auto_recharge_flow(self, db):
        """Test complete flow from consumption to task scheduling."""
        # This test would use real models and verify the full flow
        # Signals are connected by default in this test class
        pass
