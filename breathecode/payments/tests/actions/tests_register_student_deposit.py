from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments import actions, tasks
from breathecode.payments.models import AcademyPaymentSettings, CreditLedgerEntry


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
    financing = database.list_of("payments.PlanFinancing")[0]

    assert result.invoice.id == invoices[1]["id"]
    assert result.allocation.installment_applied is True
    assert result.allocation.credit_entry_type is None
    assert result.warning is None
    assert len(invoices) == 2
    assert invoices[1]["amount"] == 1200
    assert invoices[1]["externally_managed"] is True
    assert invoices[1]["invoice_kind"] == "MANUAL_DEPOSIT"
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
    assert financing["status"] == "ACTIVE"
    assert financing["status_message"] is None
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at + relativedelta(months=1)
    assert financing["valid_until"] == financing["next_payment_at"]
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
    financing = database.list_of("payments.PlanFinancing")[0]
    assert len(invoices) == 1
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

    assert exc_info.value.slug == "overpayment-exceeds-plan-total"
    assert database.list_of("payments.CreditLedgerEntry") == []
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_allows_prepayment_when_installment_already_covered(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    When the current installment is already covered by credit but future installments remain,
    the admin can still deposit to pre-pay future installments. The full amount goes as CREDIT_ADDED.

    Scenario: 4-installment plan at $300/month, $600 credit already accumulated.
    still_owed for current installment = 0, but 3 remaining installments exist.
    Depositing $300 should add it as credit — total becomes $900.
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

    # $600 credit already accumulated — covers current installment ($300) and one more.
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=600.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="overpayment on installment 2",
    )

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 300,
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    credits = database.list_of("payments.CreditLedgerEntry")
    assert result.allocation.installment_applied is False
    assert result.allocation.credit_entry_type == CreditLedgerEntry.EntryType.CREDIT_ADDED
    assert abs(result.allocation.credit_entry_amount - 300) < 1e-6
    # Total credit: 600 (prior) + 300 (new) = 900
    assert abs(result.credit_balance - 900) < 1e-6
    assert len(credits) == 2
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_rejects_when_last_installment_fully_covered(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    When the LAST installment is already fully covered by credit, deposit must be rejected.
    There are no future installments to apply extra credit to.
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

    # Credit exactly covers the last installment.
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=300.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="prior overpayment",
    )

    with pytest.raises(ValidationException) as exc_info:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 100,
                "payment_method": model.payment_method.id,
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc_info.value.slug == "overpayment-exceeds-plan-total"
    assert len(database.list_of("payments.CreditLedgerEntry")) == 1
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_intermediate_overpayment_adds_credit(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    On an intermediate installment, paying more than still_owed is allowed.
    FIFO policy applies when an installment closes with existing credit:
    consume prior credit first, then add only the deposit surplus as new credit.

    Scenario: 4-installment plan at $300/month, $100 credit already accumulated.
    still_owed = $300 - $100 = $200. Depositing $250 closes the installment,
    consumes $100 prior credit, and adds $50 new credit.
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
    assert result.allocation.credit_entry_type is None
    assert result.allocation.credit_entry_amount == pytest.approx(0, abs=1e-6)
    assert result.allocation.credit_consumed == pytest.approx(100, abs=1e-6)
    assert result.allocation.credit_added == pytest.approx(50, abs=1e-6)
    # Net credit: 100 (prior) - 100 (consumed) + 50 (new) = 50
    assert abs(result.credit_balance - 50) < 1e-6
    assert len(credits) == 3
    consumed = [c for c in credits if c["entry_type"] == "CREDIT_CONSUMED"]
    added = [c for c in credits if c["entry_type"] == "CREDIT_ADDED"]
    assert len(consumed) == 1
    assert consumed[0]["amount"] == pytest.approx(-100, abs=1e-6)
    assert len(added) == 2
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_rejects_when_deposit_exceeds_plan_total(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    A deposit that would push credit_balance above the total remaining plan value must be rejected.
    Excess credit on a PLAN_FINANCING scope can never be consumed — there are no more installments.

    Scenario: 4-installment plan at $300/month, 3 remaining installments = $900 total remaining.
    Credit already accumulated: $600. Max allowed deposit = $900 - $600 = $300.
    Depositing $400 must be rejected.
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

    # $600 credit → max_deposit = 3 × $300 - $600 = $300
    CreditLedgerEntry.objects.create(
        user=model.plan_financing.user,
        scope=CreditLedgerEntry.Scope.PLAN_FINANCING,
        plan_financing=model.plan_financing,
        amount=600.0,
        entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        notes="prior overpayment",
    )

    with pytest.raises(ValidationException) as exc_info:
        actions.register_student_deposit(
            {
                "plan_financing": model.plan_financing.id,
                "amount": 400,  # max allowed is 300
                "payment_method": model.payment_method.id,
            },
            model.proof_of_payment[1],
            model.academy.id,
            "en",
        )

    assert exc_info.value.slug == "overpayment-exceeds-plan-total"
    assert len(database.list_of("payments.CreditLedgerEntry")) == 1
    assert database.list_of("payments.PlanFinancing")[0]["status"] == "ACTIVE"


def test_register_student_deposit_outside_early_window_adds_credit_only(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    Outside early renewal window, deposits are deferred as credit and must NOT close installments.
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
            "next_payment_at": utc_now + relativedelta(days=10),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)
    AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=3)

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 300,
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    financing = database.list_of("payments.PlanFinancing")[0]
    assert result.allocation.installment_applied is False
    assert result.allocation.credit_added == pytest.approx(300, abs=1e-6)
    assert result.credit_balance == pytest.approx(300, abs=1e-6)
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == []
    assert actions.reschedule_billing_tasks.call_args_list == []


def test_register_student_deposit_inside_early_window_can_close_installment(
    database: capy.Database, monkeypatch: pytest.MonkeyPatch, utc_now
):
    """
    Inside early renewal window, a deposit that reaches installment amount can close the installment.
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
            "next_payment_at": utc_now + relativedelta(days=2),
            "valid_until": utc_now + relativedelta(months=3),
            "plan_expires_at": utc_now + relativedelta(months=12),
            "status": "ACTIVE",
            "currency_id": 1,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.plan_financing.plans.add(model.plan)
    AcademyPaymentSettings.objects.create(academy=model.academy, early_renewal_window_days=3)

    result = actions.register_student_deposit(
        {
            "plan_financing": model.plan_financing.id,
            "amount": 300,
            "payment_method": model.payment_method.id,
        },
        model.proof_of_payment[1],
        model.academy.id,
        "en",
    )

    financing = database.list_of("payments.PlanFinancing")[0]
    assert result.allocation.installment_applied is True
    assert result.allocation.credit_added == pytest.approx(0, abs=1e-6)
    assert result.credit_balance == pytest.approx(0, abs=1e-6)
    assert financing["next_payment_at"] == model.plan_financing.next_payment_at + relativedelta(months=1)
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(model.plan_financing.id)]
    assert actions.reschedule_billing_tasks.call_args_list == [call(plan_financing_id=model.plan_financing.id)]
