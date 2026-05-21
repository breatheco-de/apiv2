from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments import actions, tasks
from breathecode.payments.models import CreditLedgerEntry


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

    result = actions.register_student_deposit(
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

    assert result.deposit.id == deposits[0]["id"]
    assert result.allocation.installment_applied is True
    assert result.allocation.credit_entry_type is None
    assert result.warning is None
    assert len(invoices) == 2
    assert invoices[1]["amount"] == 1200
    assert invoices[1]["externally_managed"] is True
    assert invoices[1]["amount_breakdown"] == {
        "plans": {
            model.plan.slug: {
                "amount": 1200,
                "currency": model.currency.code,
                "type": "MANUAL_DEPOSIT_INSTALLMENT",
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


def test_register_student_deposit_overpayment_creates_credit(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    Paying more than monthly_price on an intermediate installment must:
    - Apply the installment (advance next_payment_at)
    - Create a CREDIT_ADDED ledger entry for the surplus
    - Return the surplus in credit_balance
    """
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
            "monthly_price": 400,
            "initial_payment_amount": 5000,
            "how_many_installments": 3,
            "next_payment_at": utc_now - relativedelta(days=1),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "PAYMENT_ISSUE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 600,  # 200 surplus over 400
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    credits = database.list_of("payments.CreditLedgerEntry")
    financing = database.list_of("payments.PlanFinancing")[0]

    assert result.allocation.installment_applied is True
    assert result.allocation.credit_entry_type == CreditLedgerEntry.EntryType.CREDIT_ADDED
    assert abs(result.allocation.credit_entry_amount - 200) < 1e-6
    assert abs(result.credit_balance - 200) < 1e-6
    assert result.warning is None
    assert len(credits) == 1
    assert credits[0]["amount"] == pytest.approx(200, abs=1e-6)
    assert credits[0]["entry_type"] == "CREDIT_ADDED"
    assert financing["status"] == "ACTIVE"


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


def test_register_student_deposit_partial_payment_adds_credit_and_warns(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    Paying less than monthly_price must:
    - NOT advance next_payment_at
    - Create a CREDIT_ADDED ledger entry for the partial amount
    - Return a warning about needing the full payment
    """
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
            "monthly_price": 400,
            "initial_payment_amount": 5000,
            "how_many_installments": 3,
            "next_payment_at": utc_now + relativedelta(months=1),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 150,  # partial: 150 of 400
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    credits = database.list_of("payments.CreditLedgerEntry")
    financing = database.list_of("payments.PlanFinancing")[0]

    assert result.allocation.installment_applied is False
    assert result.allocation.credit_entry_type == CreditLedgerEntry.EntryType.CREDIT_ADDED
    assert abs(result.allocation.credit_entry_amount - 150) < 1e-6
    assert abs(result.credit_balance - 150) < 1e-6
    assert result.warning is not None
    assert "150" in result.warning or "partial" in result.warning.lower() or "parcial" in result.warning.lower()
    assert len(credits) == 1
    assert credits[0]["entry_type"] == "CREDIT_ADDED"
    # next_payment_at must NOT have advanced
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == []
    assert actions.reschedule_billing_tasks.call_args_list == []


def test_register_student_deposit_last_installment_closes_plan_with_credit(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    When there is 1 installment left and prior credit covers part of it:
    - Deposit amount + credit_balance >= monthly_price → FULLY_PAID
    - A CREDIT_CONSUMED entry is created for the prior credit
    """
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
            "monthly_price": 400,
            "initial_payment_amount": 5000,
            "how_many_installments": 2,
            "next_payment_at": utc_now - relativedelta(days=1),
            "valid_until": utc_now + relativedelta(months=1),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    # Manually create a prior CREDIT_ADDED entry (e.g. from a previous partial deposit)
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=200.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="prior partial deposit",
    )

    # Now pay the remaining 200 (400 - 200 credit = 200 still owed)
    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 200,
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    credits = database.list_of("payments.CreditLedgerEntry")
    financing = database.list_of("payments.PlanFinancing")[0]

    assert result.allocation.installment_applied is True
    assert result.allocation.credit_consumed == pytest.approx(200, abs=1e-6)
    assert result.allocation.credit_entry_type == CreditLedgerEntry.EntryType.CREDIT_CONSUMED
    # After consuming 200 prior credit the net balance should be 0
    assert result.credit_balance == pytest.approx(0, abs=1e-6)
    assert financing["status"] == "FULLY_PAID"
    # credit entries: 1 prior CREDIT_ADDED + 1 new CREDIT_CONSUMED
    assert len(credits) == 2
    consumed = [c for c in credits if c["entry_type"] == "CREDIT_CONSUMED"]
    assert len(consumed) == 1
    assert consumed[0]["amount"] == pytest.approx(-200, abs=1e-6)


def test_register_student_deposit_last_installment_with_overpayment(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    When paying the last installment with an amount > still_owed, a ValidationException is raised.
    The deposit must NOT be persisted and the plan status must remain unchanged.
    """
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
            "monthly_price": 400,
            "initial_payment_amount": 5000,
            "how_many_installments": 2,
            "next_payment_at": utc_now - relativedelta(days=1),
            "valid_until": utc_now + relativedelta(months=1),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    with pytest.raises(ValidationException) as exc_info:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 500,  # 100 over the 400 monthly_price (still_owed = 400)
                "payment_method": model.payment_method.id,
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc_info.value.slug == "overpayment-on-last-installment"
    assert database.list_of("payments.CreditLedgerEntry") == []
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_rejects_when_credit_already_covers_installment(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    When the accumulated credit already covers the next installment entirely,
    a manual deposit must be rejected — the charge task will consume the credit automatically.

    Scenario: 4-installment plan at $300/month.
    - Installment 1 paid: $300 (exact).
    - Installment 2 paid: $900 → closes installment 2 + $600 credit added.
    - Attempt to deposit $300 for installment 3 → must be rejected.
    """
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
            "amount": 300,
            "paid_at": utc_now - relativedelta(months=1),
            "status": "FULFILLED",
            "externally_managed": True,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 300,
            "how_many_installments": 4,
            "next_payment_at": utc_now + relativedelta(months=1),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    # Simulate $600 credit already accumulated (e.g. from overpayment on installment 2).
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=600.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="overpayment on installment 2",
    )

    with pytest.raises(ValidationException) as exc_info:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 300,
                "payment_method": model.payment_method.id,
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc_info.value.slug == "installment-already-covered-by-credit"
    # Only the seeded credit entry should exist — no new ones.
    assert len(database.list_of("payments.CreditLedgerEntry")) == 1
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_intermediate_overpayment_adds_credit(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    On an intermediate installment, paying more than still_owed is allowed.
    The surplus beyond still_owed is recorded as CREDIT_ADDED for future installments.

    Scenario: 4-installment plan at $300/month, $100 credit already accumulated.
    still_owed = $300 - $100 = $200. Depositing $250 closes the installment
    and adds $50 as new credit (250 - 200 = 50).
    """
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
            "amount": 300,
            "paid_at": utc_now - relativedelta(months=1),
            "status": "FULFILLED",
            "externally_managed": True,
        },
        plan_financing={
            "academy_id": 1,
            "user_id": 1,
            "monthly_price": 300,
            "how_many_installments": 4,
            "next_payment_at": utc_now + relativedelta(months=1),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)

    # $100 partial credit already on record.
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=100.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="prior partial deposit",
    )

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 250,  # still_owed = 200, surplus = 50 → new credit
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    credits = database.list_of("payments.CreditLedgerEntry")
    assert result.allocation.installment_applied is True
    assert result.allocation.credit_entry_type == CreditLedgerEntry.EntryType.CREDIT_ADDED
    assert abs(result.allocation.credit_entry_amount - 50) < 1e-6
    # Total credit: 100 (prior) + 50 (new) = 150
    assert abs(result.credit_balance - 150) < 1e-6
    assert len(credits) == 2
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"
