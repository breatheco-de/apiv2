from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.actions import reschedule_billing_after_vps_next_payment_pull_forward


@pytest.mark.django_db
def test_reschedule_subscription_recreates_charge_even_if_manager_exists_true(bc):
    now = timezone.now()
    model = bc.database.create(
        academy=1,
        user=1,
        subscription={
            "next_payment_at": now + timedelta(days=30),
            "valid_until": now + timedelta(days=30),
            "seat_service_item_id": None,
        },
    )
    sub = model.subscription

    charge_manager = MagicMock()
    charge_manager.exists.return_value = True
    notify_manager = MagicMock()

    def schedule_task_side_effect(fn, *_args, **_kwargs):
        if fn == tasks.charge_subscription:
            return charge_manager
        if fn == tasks.notify_subscription_renewal:
            return notify_manager
        return MagicMock()

    with patch(
        "breathecode.payments.actions._cancel_pending_future_scheduled",
        MagicMock(),
    ), patch(
        "task_manager.django.actions.schedule_task",
        side_effect=schedule_task_side_effect,
    ):
        reschedule_billing_after_vps_next_payment_pull_forward(subscription_id=sub.id)

    charge_manager.call.assert_called_once_with(sub.id)
