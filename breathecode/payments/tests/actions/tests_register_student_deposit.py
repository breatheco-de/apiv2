from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments import actions, tasks


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_register_student_deposit_applies_payment_to_plan_financing(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    monkeypatch.setattr(actions.timezone, "now", MagicMock(return_value=utc_now))
    monkeypatch.setattr(tasks.renew_plan_financing_consumables, "delay", MagicMock())
    monkeypatch.setattr(actions, "reschedule_billing_tasks", MagicMock())

    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan={"is_renewable": False},
        currency=1,
        proof_of_payment=2,
        payment_method={"currency_id": 1, "is_credit_card": False, "is_crypto": False},
        bag={"was_delivered": True},
        invoice={
            "amount": 5000,
            "paid_at": utc_now - relativedelta(months=2),
            "status": "FULFILLED",
            "externally_managed": True,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 1200,
            "initial_payment_amount": 5000,
            "how_many_installments": 2,
            "next_payment_at": utc_now - relativedelta(days=1),
            "valid_until": utc_now + relativedelta(months=2),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "PAYMENT_ISSUE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    deposit = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 1200,
            "payment_method": model.payment_method.id,
            "notes": "Cash payment",
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    invoices = database.list_of("payments.Invoice")
    deposits = database.list_of("payments.StudentDeposit")
    financing = database.list_of("payments.PlanFinancing")[0]

    assert deposit.id == deposits[0]["id"]
    assert len(invoices) == 2
    assert invoices[1]["amount"] == 1200
    assert invoices[1]["externally_managed"] is True
    assert invoices[1]["amount_breakdown"] == {
        "plans": {
            model.plan.slug: {
                "amount": 1200,
                "currency": model.currency.code,
                "type": "MANUAL_DEPOSIT",
            }
        },
        "service-items": {},
    }
    assert deposits[0]["user_id"] == model.user.id
    assert deposits[0]["academy_id"] == model.academy.id
    assert deposits[0]["invoice_id"] == invoices[1]["id"]
    assert deposits[0]["plan_financing_id"] == model.plan_financing.id
    assert deposits[0]["amount"] == 1200
    assert deposits[0]["status"] == "APPLIED"
    assert deposits[0]["notes"] == "Cash payment"
    assert deposits[0]["applied_at"] == utc_now
    assert financing["status"] == "ACTIVE"
    assert financing["status_message"] is None
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at + relativedelta(months=1)
    assert financing["valid_until"] == model.plan_financing.valid_until + relativedelta(months=1)
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(model.plan_financing.id)]
    assert actions.reschedule_billing_tasks.call_args_list == [
        call(plan_financing_id=model.plan_financing.id)
    ]


def test_register_student_deposit_rejects_amount_above_monthly_price(
    database: capy.Database, utc_now
):
    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan={"is_renewable": False},
        currency=1,
        proof_of_payment=2,
        payment_method={"currency_id": 1, "is_credit_card": False, "is_crypto": False},
        bag={"was_delivered": True},
        invoice={
            "amount": 5000,
            "paid_at": utc_now - relativedelta(months=2),
            "status": "FULFILLED",
            "externally_managed": True,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 400,
            "initial_payment_amount": 5000,
            "how_many_installments": 2,
            "next_payment_at": utc_now - relativedelta(days=1),
            "valid_until": utc_now + relativedelta(months=2),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "PAYMENT_ISSUE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    with pytest.raises(ValidationException) as exc:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 500,
                "payment_method": model.payment_method.id,
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc.value.detail == "deposit-amount-exceeds-monthly-price"


def test_register_student_deposit_rejects_when_no_installments_remaining(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    If the user already paid all expected installments (e.g. one-payment: 1/1),
    /deposit must reject and must not create a new invoice or move next_payment_at forward.
    """
    monkeypatch.setattr(actions.timezone, "now", MagicMock(return_value=utc_now))
    monkeypatch.setattr(actions, "reschedule_billing_tasks", MagicMock())
    monkeypatch.setattr(tasks.renew_plan_financing_consumables, "delay", MagicMock())

    model = database.create(
        country=1,
        city=1,
        academy=1,
        user=1,
        plan={"is_renewable": False},
        currency=1,
        proof_of_payment=2,
        payment_method={"currency_id": 1, "is_credit_card": False, "is_crypto": False},
        bag={"was_delivered": True},
        invoice={
            "amount": 4000,
            "paid_at": utc_now - relativedelta(days=1),
            "status": "FULFILLED",
            "externally_managed": True,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 4000,
            "initial_payment_amount": None,
            "how_many_installments": 1,
            "next_payment_at": utc_now + relativedelta(months=1),
            "valid_until": utc_now,
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    with pytest.raises(ValidationException) as exc:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 100,
                "payment_method": model.payment_method.id,
                "notes": "Late cash",
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc.value.detail == "no-remaining-installments"
    invoices = database.list_of("payments.Invoice")
    deposits = database.list_of("payments.StudentDeposit")
    financing = database.list_of("payments.PlanFinancing")[0]
    assert len(invoices) == 1
    assert deposits == []
    assert financing["status"] == "ACTIVE"
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at
    assert actions.reschedule_billing_tasks.call_args_list == []
