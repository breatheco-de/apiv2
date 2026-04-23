"""
Tras un adelanto manual de ``next_payment_at`` (como el que aplica ``apply_early_vps_billing_alignment``),
``renew_subscription_consumables`` / ``renew_plan_financing_consumables`` + ``renew_consumables`` vuelven a
fijar ``ServiceStockScheduler.valid_until`` acorde al recurso (p. ej. tope por ``next_payment_at`` en suscripción
cuando ``subscription.valid_until`` es nulo en ``renew_consumables``).
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.models import PlanFinancing, ServiceStockScheduler, Subscription
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

    with patch.object(
        tasks.renew_subscription_consumables,
        "delay",
        MagicMock(
            side_effect=lambda sid, seat_id=None: tasks.renew_subscription_consumables.apply(
                args=[sid], kwargs={"seat_id": seat_id} if seat_id else {}, throw=True
            )
        ),
    ), patch.object(
        tasks.renew_consumables,
        "delay",
        MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
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

    with patch.object(
        tasks.renew_plan_financing_consumables,
        "delay",
        MagicMock(
            side_effect=lambda pid, seat_id=None: tasks.renew_plan_financing_consumables.apply(
                args=[pid], kwargs={"seat_id": seat_id} if seat_id is not None else {}, throw=True
            )
        ),
    ), patch.object(
        tasks.renew_consumables,
        "delay",
        MagicMock(side_effect=lambda scheduler_id: tasks.renew_consumables.apply(args=[scheduler_id], throw=True)),
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
