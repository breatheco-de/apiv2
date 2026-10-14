"""Dry-run and apply behavior for consumables issued two renew periods ahead."""

from datetime import datetime, timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.core.management import call_command

from breathecode.payments.models import Consumable, PlanFinancing, ServiceStockScheduler

pytestmark = pytest.mark.django_db

CREATED = datetime(2026, 10, 14, 17, 0, tzinfo=dt_timezone.utc)


def _stock(
    bc,
    *,
    renew_at=1,
    periods=2,
    status="FULLY_PAID",
    extra_consumable=False,
    expires_at=None,
    created=CREATED,
):
    delta = relativedelta(months=renew_at)
    valid_until = created + delta
    for _ in range(periods - 1):
        valid_until = valid_until + delta
    plan_expires_at = expires_at or created + relativedelta(months=12)
    model = bc.database.create(
        user={"email": "fully-paid@example.com"},
        academy=1,
        plan={"is_renewable": False, "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": status,
            "how_many_installments": 1,
            "installments_paid": 1,
            "monthly_price": 100,
            "next_payment_at": created + relativedelta(months=1),
            "valid_until": created + relativedelta(months=6),
            "plan_expires_at": plan_expires_at,
        },
        service={"type": "VOID"},
        service_item={"renew_at": renew_at, "renew_at_unit": "MONTH", "how_many": 1, "service_id": 1},
        plan_service_item={"plan_id": 1, "service_item_id": 1},
        plan_service_item_handler={"handler_id": 1, "plan_financing_id": 1, "subscription_id": None},
        service_stock_scheduler={
            "subscription_handler_id": None,
            "plan_handler_id": 1,
            "valid_until": valid_until,
        },
        consumable={
            "valid_until": valid_until,
            "service_item_id": 1,
            "user_id": 1,
            "how_many": 1,
        },
    )
    PlanFinancing.objects.filter(pk=model.plan_financing.id).update(created_at=created)
    Consumable.objects.filter(pk=model.consumable.id).update(plan_financing=model.plan_financing)
    model.service_stock_scheduler.consumables.add(model.consumable)
    if extra_consumable:
        extra = bc.database.create(
            consumable={
                "valid_until": valid_until,
                "service_item_id": 1,
                "user_id": 1,
                "how_many": 1,
            }
        ).consumable
        Consumable.objects.filter(pk=extra.id).update(plan_financing=model.plan_financing)
        model.service_stock_scheduler.consumables.add(extra)
    model.plan_financing.refresh_from_db()
    model.consumable.refresh_from_db()
    model.service_stock_scheduler.refresh_from_db()
    return model


def _run(*args):
    out = StringIO()
    with patch(
        "breathecode.payments.management.commands.fix_fully_paid_double_period.timezone.now",
        return_value=CREATED,
    ):
        call_command("fix_fully_paid_double_period", *args, stdout=out)
    return out.getvalue()


def test_dry_run_prints_the_correction_and_does_not_save(bc):
    model = _stock(bc)
    one_period = CREATED + relativedelta(months=1)

    output = _run()

    assert "Would update 1 scheduler" in output
    assert str(one_period) in output
    model.consumable.refresh_from_db()
    model.service_stock_scheduler.refresh_from_db()
    assert model.consumable.valid_until != one_period
    assert model.service_stock_scheduler.valid_until != one_period


def test_apply_moves_the_consumable_and_the_scheduler_back_one_period(bc):
    model = _stock(bc, renew_at=4, periods=2)
    one_period = CREATED + relativedelta(months=4)

    output = _run("--apply")

    assert "Updated 1 scheduler" in output
    model.consumable.refresh_from_db()
    model.service_stock_scheduler.refresh_from_db()
    assert model.consumable.valid_until == one_period
    assert model.service_stock_scheduler.valid_until == one_period


def test_skips_a_scheduler_with_two_consumables(bc):
    model = _stock(bc, extra_consumable=True)
    before = model.consumable.valid_until

    output = _run("--apply")

    assert "Updated 0 scheduler" in output
    model.consumable.refresh_from_db()
    assert model.consumable.valid_until == before


def test_skips_a_plan_that_still_owes_installments(bc):
    model = _stock(bc, status="ACTIVE")
    before = model.consumable.valid_until

    output = _run("--apply")

    assert "Updated 0 scheduler" in output
    model.consumable.refresh_from_db()
    assert model.consumable.valid_until == before


def test_skips_when_the_date_is_plan_expires_at(bc):
    expires = CREATED + relativedelta(months=1) + relativedelta(months=1)
    model = _stock(bc, expires_at=expires)
    ServiceStockScheduler.objects.filter(pk=model.service_stock_scheduler.id).update(valid_until=expires)
    Consumable.objects.filter(pk=model.consumable.id).update(valid_until=expires)

    output = _run("--apply")

    assert "Updated 0 scheduler" in output
    model.consumable.refresh_from_db()
    assert model.consumable.valid_until == expires


def test_skips_a_doubled_period_that_already_ended(bc):
    created = datetime(2026, 1, 14, 17, 0, tzinfo=dt_timezone.utc)
    model = _stock(bc, created=created)
    before = created + relativedelta(months=2)

    output = _run("--apply")

    assert "Updated 0 scheduler" in output
    model.consumable.refresh_from_db()
    model.service_stock_scheduler.refresh_from_db()
    assert model.consumable.valid_until == before
    assert model.service_stock_scheduler.valid_until == before


def test_skips_stock_that_already_covers_one_period(bc):
    model = _stock(bc, periods=1)
    one_period = CREATED + relativedelta(months=1)

    output = _run("--apply")

    assert "Updated 0 scheduler" in output
    model.consumable.refresh_from_db()
    assert model.consumable.valid_until == one_period
