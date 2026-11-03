"""
Tras un adelanto manual de ``next_payment_at`` (como el que aplica ``apply_early_vps_billing_alignment``),
``renew_subscription_consumables`` / ``renew_plan_financing_consumables`` + ``renew_consumables`` vuelven a
fijar ``ServiceStockScheduler.valid_until`` acorde al recurso (p. ej. tope por ``next_payment_at`` en suscripción
cuando ``subscription.valid_until`` es nulo en ``renew_consumables``).
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from task_manager.core.exceptions import AbortTask

from breathecode.payments import tasks
from breathecode.payments.models import Consumable, PlanFinancing, ServiceStockScheduler, Subscription
from breathecode.provisioning.actions import NEXT_CHARGE_PULL_FORWARD


@pytest.mark.django_db
def test_renew_subscription_plan_scheduler_capped_by_next_payment_after_pull(bc):
    utc = timezone.now()
    next_payment = utc + relativedelta(months=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        subscription={
            "next_payment_at": next_payment,
            "valid_until": None,
            "seat_service_item_id": None,
        },
        plan={"is_renewable": False},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "YEAR"},
        subscription_service_item={"subscription_id": 1, "service_item_id": 1},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )
    sub = model.subscription

    with (
        patch.object(
            tasks.renew_subscription_consumables,
            "delay",
            MagicMock(
                side_effect=lambda sid, seat_id=None: tasks.renew_subscription_consumables.apply(
                    args=[sid], kwargs={"seat_id": seat_id} if seat_id else {}, throw=True
                )
            ),
        ),
        patch.object(
            tasks.renew_consumables,
            "delay",
            MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
        ),
    ):
        tasks.build_service_stock_scheduler_from_subscription.apply(kwargs={"subscription_id": sub.id}, throw=True)

    scheduler = ServiceStockScheduler.objects.filter(plan_handler__subscription=sub).first()
    assert scheduler is not None
    assert scheduler.valid_until == next_payment

    pulled = next_payment - NEXT_CHARGE_PULL_FORWARD
    Subscription.objects.filter(pk=sub.pk).update(next_payment_at=pulled)

    with patch.object(
        tasks.renew_consumables,
        "delay",
        MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
    ):
        tasks.renew_subscription_consumables.apply(args=[sub.id], throw=True)

    scheduler.refresh_from_db()
    sub.refresh_from_db()
    assert sub.next_payment_at == pulled
    assert scheduler.valid_until <= sub.next_payment_at


@pytest.mark.django_db
def test_renew_plan_financing_scheduler_stays_within_plan_expires_after_pull(bc):
    utc = timezone.now()
    next_payment = utc + relativedelta(months=1)
    plan_expires = utc + relativedelta(years=1)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": next_payment,
            "valid_until": utc + relativedelta(months=6),
            "plan_expires_at": plan_expires,
            "monthly_price": 100,
            "status": "ACTIVE",
        },
        plan={"is_renewable": False},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "YEAR"},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )
    pf = model.plan_financing

    with (
        patch.object(
            tasks.renew_plan_financing_consumables,
            "delay",
            MagicMock(
                side_effect=lambda pid, seat_id=None: tasks.renew_plan_financing_consumables.apply(
                    args=[pid], kwargs={"seat_id": seat_id} if seat_id is not None else {}, throw=True
                )
            ),
        ),
        patch.object(
            tasks.renew_consumables,
            "delay",
            MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
        ),
    ):
        tasks.build_service_stock_scheduler_from_plan_financing.apply(kwargs={"plan_financing_id": pf.id}, throw=True)

    scheduler = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=pf).first()
    assert scheduler is not None
    assert scheduler.valid_until <= pf.plan_expires_at

    pulled = next_payment - NEXT_CHARGE_PULL_FORWARD
    PlanFinancing.objects.filter(pk=pf.pk).update(next_payment_at=pulled)

    with patch.object(
        tasks.renew_consumables,
        "delay",
        MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
    ):
        tasks.renew_plan_financing_consumables.apply(args=[pf.id], throw=True)

    scheduler.refresh_from_db()
    pf.refresh_from_db()
    assert pf.next_payment_at == pulled
    assert scheduler.valid_until <= pf.plan_expires_at


@pytest.mark.django_db
def test_fully_paid_first_consumable_covers_one_renew_period(bc):
    """FULLY_PAID must not seed the scheduler one period ahead of the renew that follows."""
    utc = timezone.now()
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": utc + relativedelta(months=1),
            "valid_until": utc + relativedelta(months=1),
            "plan_expires_at": utc + relativedelta(months=6),
            "monthly_price": 100,
            "status": "FULLY_PAID",
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        plan={"is_renewable": False, "time_of_life": 6, "time_of_life_unit": "MONTH"},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "MONTH"},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )
    pf = model.plan_financing

    with (
        patch.object(
            tasks.renew_plan_financing_consumables,
            "delay",
            MagicMock(side_effect=_forward_plan_renewal),
        ),
        patch.object(
            tasks.renew_consumables,
            "delay",
            MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
        ),
        patch(
            "breathecode.payments.tasks.timezone.now",
            return_value=utc,
        ),
    ):
        tasks.build_service_stock_scheduler_from_plan_financing.apply(kwargs={"plan_financing_id": pf.id}, throw=True)

    scheduler = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=pf).first()
    consumable = Consumable.objects.get(plan_financing=pf)
    one_period = utc + relativedelta(months=1)

    assert scheduler is not None
    assert scheduler.valid_until == one_period
    assert consumable.valid_until == one_period


def _apply_renew(scheduler_id: int) -> None:
    try:
        tasks.renew_consumables.apply(args=[scheduler_id], throw=True)
    except AbortTask:
        return


def _forward_plan_renewal(pid, seat_id=None, service_ids=None, scheduler_ids=None):
    tasks.renew_plan_financing_consumables.apply(
        args=[pid],
        kwargs={
            k: v
            for k, v in {
                "seat_id": seat_id,
                "service_ids": service_ids,
                "scheduler_ids": scheduler_ids,
            }.items()
            if v is not None
        },
        throw=True,
    )


def _build_financing_stock(plan_financing_id: int) -> None:
    with (
        patch.object(
            tasks.renew_plan_financing_consumables,
            "delay",
            MagicMock(side_effect=_forward_plan_renewal),
        ),
        patch.object(
            tasks.renew_consumables,
            "delay",
            MagicMock(side_effect=_apply_renew),
        ),
    ):
        tasks.build_service_stock_scheduler_from_plan_financing.apply(
            kwargs={"plan_financing_id": plan_financing_id}, throw=True
        )


@pytest.mark.django_db
def test_fully_paid_rebuild_keeps_the_current_cycle(bc):
    """Rebuilding a FULLY_PAID scheduler must not shift its anniversary or add a consumable."""
    utc = timezone.now()
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": utc + relativedelta(months=1),
            "valid_until": utc + relativedelta(months=1),
            "plan_expires_at": utc + relativedelta(months=6),
            "monthly_price": 100,
            "status": "FULLY_PAID",
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        plan={"is_renewable": False, "time_of_life": 6, "time_of_life_unit": "MONTH"},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "MONTH"},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )

    with patch("breathecode.payments.tasks.timezone.now", return_value=utc):
        _build_financing_stock(model.plan_financing.id)
        _build_financing_stock(model.plan_financing.id)

    cycle_end = utc + relativedelta(months=1)
    schedulers = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=model.plan_financing)
    consumables = Consumable.objects.filter(plan_financing=model.plan_financing)

    assert list(schedulers.values_list("valid_until", flat=True)) == [cycle_end]
    assert list(consumables.values_list("valid_until", flat=True)) == [cycle_end]


@pytest.mark.django_db
def test_fully_paid_rebuild_keeps_each_service_renew_period(bc):
    """A longer renew period must not pull shorter services forward on rebuild."""
    utc = timezone.now()
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": utc + relativedelta(months=1),
            "valid_until": utc + relativedelta(months=1),
            "plan_expires_at": utc + relativedelta(months=6),
            "monthly_price": 100,
            "status": "FULLY_PAID",
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        plan={"is_renewable": False, "time_of_life": 6, "time_of_life_unit": "MONTH"},
        service=[{"type": "VOID"}, {"type": "VOID"}],
        service_item=[
            {"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "MONTH"},
            {"service_id": 2, "how_many": 1, "renew_at": 4, "renew_at_unit": "MONTH"},
        ],
        plan_service_item=[
            {"plan_id": 1, "service_item_id": 1},
            {"plan_id": 1, "service_item_id": 2},
        ],
    )
    monthly_item, longer_item = model.service_item

    with patch("breathecode.payments.tasks.timezone.now", return_value=utc):
        _build_financing_stock(model.plan_financing.id)
        _build_financing_stock(model.plan_financing.id)

    expected = {
        monthly_item.id: utc + relativedelta(months=1),
        longer_item.id: utc + relativedelta(months=4),
    }
    consumables = Consumable.objects.filter(plan_financing=model.plan_financing)
    schedulers = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=model.plan_financing)

    assert {row.service_item_id: row.valid_until for row in consumables} == expected
    assert {
        row.plan_handler.handler.service_item_id: row.valid_until
        for row in schedulers.select_related("plan_handler__handler")
    } == expected


@pytest.mark.django_db
def test_fully_paid_rebuild_keeps_a_month_end_anniversary(bc):
    """Rebuilding must not round a day-31 anniversary down by subtracting a month."""
    utc = datetime(2026, 1, 31, 12, 0, tzinfo=dt_timezone.utc)
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": utc + relativedelta(months=1),
            "valid_until": utc + relativedelta(months=1),
            "plan_expires_at": utc + relativedelta(months=6),
            "monthly_price": 100,
            "status": "FULLY_PAID",
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        plan={"is_renewable": False, "time_of_life": 6, "time_of_life_unit": "MONTH"},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "MONTH"},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )

    with patch("breathecode.payments.tasks.timezone.now", return_value=utc):
        _build_financing_stock(model.plan_financing.id)
        _build_financing_stock(model.plan_financing.id)

    # 2026 is not a leap year: Jan 31 + 1 month lands on Feb 28, and stays there.
    cycle_end = utc + relativedelta(months=1)
    schedulers = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=model.plan_financing)
    consumables = Consumable.objects.filter(plan_financing=model.plan_financing)

    assert cycle_end == datetime(2026, 2, 28, 12, 0, tzinfo=dt_timezone.utc)
    assert list(schedulers.values_list("valid_until", flat=True)) == [cycle_end]
    assert list(consumables.values_list("valid_until", flat=True)) == [cycle_end]


@pytest.mark.django_db
def test_fully_paid_rebuild_renews_an_expired_consumable(bc):
    """An expired FULLY_PAID consumable is renewed from its stored date, not from now."""
    utc = timezone.now()
    model = bc.database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan_financing={
            "next_payment_at": utc + relativedelta(months=1),
            "valid_until": utc + relativedelta(months=1),
            "plan_expires_at": utc + relativedelta(months=6),
            "monthly_price": 100,
            "status": "FULLY_PAID",
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        plan={"is_renewable": False, "time_of_life": 6, "time_of_life_unit": "MONTH"},
        service={"type": "VOID"},
        service_item={"service_id": 1, "how_many": 1, "renew_at": 1, "renew_at_unit": "MONTH"},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
    )
    expired = utc - relativedelta(days=1)

    with patch("breathecode.payments.tasks.timezone.now", return_value=utc):
        _build_financing_stock(model.plan_financing.id)
        Consumable.objects.filter(plan_financing=model.plan_financing).update(valid_until=expired)
        ServiceStockScheduler.objects.filter(plan_handler__plan_financing=model.plan_financing).update(
            valid_until=expired
        )
        _build_financing_stock(model.plan_financing.id)

    next_cycle = expired + relativedelta(months=1)
    schedulers = ServiceStockScheduler.objects.filter(plan_handler__plan_financing=model.plan_financing)
    consumables = Consumable.objects.filter(plan_financing=model.plan_financing)

    assert list(schedulers.values_list("valid_until", flat=True)) == [next_cycle]
    assert set(consumables.values_list("valid_until", flat=True)) == {expired, next_cycle}
