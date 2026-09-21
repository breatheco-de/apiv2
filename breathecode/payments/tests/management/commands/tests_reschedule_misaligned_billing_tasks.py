from datetime import timedelta
from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from django.utils import timezone
from task_manager.django.models import ScheduledTask

from breathecode.payments.actions import SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT
from breathecode.payments.management.commands.reschedule_misaligned_billing_tasks import Command

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")

PAID_PLAN = {
    "is_renewable": True,
    "price_per_month": 10.0,
    "price_per_quarter": 30.0,
    "price_per_half": 60.0,
    "price_per_year": 100.0,
}


@pytest.fixture(autouse=True)
def patch_now_and_reschedule(monkeypatch: pytest.MonkeyPatch):
    reschedule = MagicMock()
    monkeypatch.setattr(
        "breathecode.payments.management.commands.reschedule_misaligned_billing_tasks.reschedule_billing_tasks",
        reschedule,
    )
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    return reschedule


def _create_scheduled_charge(*, task_name: str, entity_id: int, eta, duration=None):
    if duration is None:
        duration = eta - UTC_NOW if eta > UTC_NOW else timedelta(seconds=60)
    return ScheduledTask.objects.create(
        task_module="breathecode.payments.tasks",
        task_name=task_name,
        arguments={"args": [entity_id], "kwargs": {}},
        status="PENDING",
        eta=eta,
        duration=duration,
    )


def _handle(**kwargs):
    defaults = {
        "dry_run": False,
        "email": None,
        "subscription_id": None,
        "plan_financing_id": None,
    }
    defaults.update(kwargs)
    Command().handle(**defaults)


def test_reschedules_subscription_when_eta_before_next_payment_at(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user={"email": "sub@example.com"},
        plan=PAID_PLAN,
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )
    # Truncated-days bug: ETA ~1 day early
    _create_scheduled_charge(
        task_name="charge_subscription",
        entity_id=model.subscription.id,
        eta=next_at - timedelta(days=1),
    )

    _handle()

    patch_now_and_reschedule.assert_called_once_with(subscription_id=model.subscription.id)


def test_skips_aligned_subscription_eta(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user=1,
        plan=PAID_PLAN,
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )
    _create_scheduled_charge(
        task_name="charge_subscription",
        entity_id=model.subscription.id,
        eta=next_at + SCHEDULE_CHARGE_LAG_AFTER_NEXT_PAYMENT,
    )

    _handle()

    patch_now_and_reschedule.assert_not_called()


def test_reschedules_plan_financing_when_eta_before_next_payment_at(
    database: capy.Database, patch_now_and_reschedule
):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user={"email": "pf@example.com"},
        plan={"is_renewable": False},
        plan_financing={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at + timedelta(days=90),
            "plan_expires_at": next_at + timedelta(days=365),
            "how_many_installments": 5,
            "installments_paid": 1,
            "monthly_price": 100.0,
        },
    )
    _create_scheduled_charge(
        task_name="charge_plan_financing",
        entity_id=model.plan_financing.id,
        eta=next_at - timedelta(days=1),
    )

    _handle()

    patch_now_and_reschedule.assert_called_once_with(plan_financing_id=model.plan_financing.id)


def test_dry_run_does_not_reschedule(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user=1,
        plan=PAID_PLAN,
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )
    _create_scheduled_charge(
        task_name="charge_subscription",
        entity_id=model.subscription.id,
        eta=next_at - timedelta(days=1),
    )

    _handle(dry_run=True)

    patch_now_and_reschedule.assert_not_called()


def test_schedules_active_without_pending_charge(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user=1,
        plan=PAID_PLAN,
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )

    _handle()

    patch_now_and_reschedule.assert_called_once_with(subscription_id=model.subscription.id)


def test_skips_missing_schedule_for_seat_subscriptions(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user=1,
        plan=PAID_PLAN,
        service=1,
        service_item={"how_many": 3},
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
        },
    )
    model.subscription.seat_service_item = model.service_item
    model.subscription.save(update_fields=["seat_service_item"])

    _handle()

    patch_now_and_reschedule.assert_not_called()


def test_skips_free_subscription_without_pending_charge(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    database.create(
        academy=1,
        user=1,
        plan={
            "is_renewable": True,
            "price_per_month": 0,
            "price_per_quarter": 0,
            "price_per_half": 0,
            "price_per_year": 0,
        },
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )

    _handle()

    patch_now_and_reschedule.assert_not_called()


def test_email_filter(database: capy.Database, patch_now_and_reschedule):
    next_at = UTC_NOW + timedelta(days=30)
    model = database.create(
        academy=1,
        user={"email": "keep@example.com"},
        plan=PAID_PLAN,
        subscription={
            "status": "ACTIVE",
            "next_payment_at": next_at,
            "valid_until": next_at,
            "seat_service_item_id": None,
        },
    )
    _create_scheduled_charge(
        task_name="charge_subscription",
        entity_id=model.subscription.id,
        eta=next_at - timedelta(days=1),
    )

    _handle(email="other@example.com")

    patch_now_and_reschedule.assert_not_called()
