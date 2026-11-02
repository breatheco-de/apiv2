from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.actions import (
    SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT,
    reschedule_billing_tasks,
)


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
    scheduled: list[tuple] = []

    def schedule_task_side_effect(fn, eta, *args, **kwargs):
        scheduled.append((fn, eta))
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
    ), patch("breathecode.payments.actions.timezone.now", return_value=now):
        reschedule_billing_tasks(subscription_id=sub.id)

    charge_manager.call.assert_called_once_with(sub.id)
    charge_etas = [eta for fn, eta in scheduled if fn == tasks.charge_subscription]
    assert len(charge_etas) == 1
    assert str(charge_etas[0]).endswith("s")
    sub.refresh_from_db()
    want_seconds = int(
        (sub.next_payment_at + SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT - now).total_seconds()
    )
    assert int(str(charge_etas[0])[:-1]) == want_seconds


def _plan_financing_schedule_side_effect(scheduled, charge_manager, notify_manager):
    def schedule_task_side_effect(fn, eta, *args, **kwargs):
        scheduled.append((fn, eta))
        if fn == tasks.charge_plan_financing:
            return charge_manager
        if fn == tasks.notify_plan_financing_renewal:
            return notify_manager
        return MagicMock()

    return schedule_task_side_effect


@pytest.mark.usefixtures("db")
def test_reschedule_plan_financing_skips_notify_when_created_by_admin(database: capy.Database):
    now = timezone.now()
    model = database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "next_payment_at": now + timedelta(days=30),
            "valid_until": now + timedelta(days=180),
            "plan_expires_at": now + timedelta(days=365),
            "how_many_installments": 12,
            "installments_paid": 1,
            "monthly_price": 200,
            "created_by_admin": True,
            "status": "ACTIVE",
        },
    )
    plan_financing = model.plan_financing
    plan_financing.plans.add(model.plan)

    charge_manager = MagicMock()
    notify_manager = MagicMock()
    scheduled: list[tuple] = []

    with patch(
        "breathecode.payments.actions._cancel_pending_future_scheduled",
        MagicMock(),
    ), patch(
        "task_manager.django.actions.schedule_task",
        side_effect=_plan_financing_schedule_side_effect(scheduled, charge_manager, notify_manager),
    ), patch("breathecode.payments.actions.timezone.now", return_value=now):
        reschedule_billing_tasks(plan_financing_id=plan_financing.id)

    charge_manager.call.assert_called_once_with(plan_financing.id)
    notify_manager.call.assert_not_called()
    assert [fn for fn, _eta in scheduled] == [tasks.charge_plan_financing]


@pytest.mark.usefixtures("db")
def test_reschedule_plan_financing_schedules_notify_when_not_created_by_admin(database: capy.Database):
    now = timezone.now()
    model = database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "next_payment_at": now + timedelta(days=30),
            "valid_until": now + timedelta(days=180),
            "plan_expires_at": now + timedelta(days=365),
            "how_many_installments": 12,
            "installments_paid": 1,
            "monthly_price": 200,
            "created_by_admin": False,
            "status": "ACTIVE",
        },
    )
    plan_financing = model.plan_financing
    plan_financing.plans.add(model.plan)

    charge_manager = MagicMock()
    notify_manager = MagicMock()
    scheduled: list[tuple] = []

    with patch(
        "breathecode.payments.actions._cancel_pending_future_scheduled",
        MagicMock(),
    ), patch(
        "task_manager.django.actions.schedule_task",
        side_effect=_plan_financing_schedule_side_effect(scheduled, charge_manager, notify_manager),
    ), patch("breathecode.payments.actions.timezone.now", return_value=now):
        reschedule_billing_tasks(plan_financing_id=plan_financing.id)

    charge_manager.call.assert_called_once_with(plan_financing.id)
    notify_manager.call.assert_called_once_with(plan_financing.id)
    assert [fn for fn, _eta in scheduled] == [
        tasks.charge_plan_financing,
        tasks.notify_plan_financing_renewal,
    ]
