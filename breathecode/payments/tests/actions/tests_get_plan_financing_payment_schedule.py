from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta

from breathecode.payments import actions


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_get_plan_financing_payment_schedule_builds_summary_and_schedule(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    monkeypatch.setattr(actions.timezone, "now", MagicMock(return_value=utc_now))

    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan=1,
        currency={"code": "USD"},
        bag={"was_delivered": True},
        invoice={
            "amount": 100.0,
            "paid_at": utc_now - relativedelta(months=1),
            "status": "FULFILLED",
            "amount_refunded": 0.0,
            "currency_id": 1,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 100.0,
            "how_many_installments": 3,
            "installments_paid": 1,
            "next_payment_at": utc_now,
            "valid_until": utc_now + relativedelta(months=2),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    result = actions.get_plan_financing_payment_schedule(model.plan_financing, lang="en")

    assert result["summary"]["paid_so_far"] == pytest.approx(100.0, abs=1e-6)
    assert result["summary"]["plan_financing_id"] == model.plan_financing.id
    assert result["summary"]["plan_slug"] == model.plan.slug
    assert result["summary"]["negotiated_total"] == pytest.approx(300.0, abs=1e-6)
    assert result["summary"]["pending_amount"] == pytest.approx(200.0, abs=1e-6)
    assert result["summary"]["payments_made"] == 1
    assert result["summary"]["total_payments"] == 3
    assert result["summary"]["currency"] == "USD"
    assert result["summary"]["on_time_rate"] == pytest.approx(100.0, abs=1e-6)

    assert len(result["schedule"]) == 3
    assert result["schedule"][0]["installment_number"] == 1
    assert result["schedule"][0]["status"] == "PAID_ON_TIME"
    assert result["schedule"][1]["status"] in ["PENDING", "OVERDUE"]


def test_get_plan_financing_payment_schedule_same_day_payment_is_on_time(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    due_date = utc_now.replace(hour=9, minute=0, second=0, microsecond=0)
    paid_at = due_date + relativedelta(hours=10)
    monkeypatch.setattr(actions.timezone, "now", MagicMock(return_value=due_date))

    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan=1,
        currency={"code": "USD"},
        bag={"was_delivered": True},
        invoice={
            "amount": 100.0,
            "paid_at": paid_at,
            "status": "FULFILLED",
            "amount_refunded": 0.0,
            "currency_id": 1,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 100.0,
            "how_many_installments": 2,
            "installments_paid": 1,
            "next_payment_at": due_date + relativedelta(months=1),
            "valid_until": due_date + relativedelta(months=2),
            "plan_expires_at": due_date + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    result = actions.get_plan_financing_payment_schedule(model.plan_financing, lang="en")
    assert result["schedule"][0]["status"] == "PAID_ON_TIME"


def test_get_plan_financing_payment_schedule_next_day_payment_is_late(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    due_date = utc_now.replace(hour=9, minute=0, second=0, microsecond=0)
    paid_at = due_date + relativedelta(days=1)
    monkeypatch.setattr(actions.timezone, "now", MagicMock(return_value=due_date))

    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan=1,
        currency={"code": "USD"},
        bag={"was_delivered": True},
        invoice={
            "amount": 100.0,
            "paid_at": paid_at,
            "status": "FULFILLED",
            "amount_refunded": 0.0,
            "currency_id": 1,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 100.0,
            "how_many_installments": 2,
            "installments_paid": 1,
            "next_payment_at": due_date + relativedelta(months=1),
            "valid_until": due_date + relativedelta(months=2),
            "plan_expires_at": due_date + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    result = actions.get_plan_financing_payment_schedule(model.plan_financing, lang="en")
    assert result["schedule"][0]["status"] == "PAID_LATE"
