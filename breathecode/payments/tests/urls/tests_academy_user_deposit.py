from unittest.mock import MagicMock

import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.request import Request

from breathecode.payments import actions
from breathecode.payments.actions import DepositAllocation, DepositResult
from breathecode.payments.models import CreditLedgerEntry
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


def _make_deposit_result(invoice, *, installment_applied=True, credit_entry_amount=0.0,
                         credit_entry_type=None, credit_consumed=0.0,
                         credit_balance=0.0, remaining_installments=1, warning=None):
    allocation = DepositAllocation(
        installment_applied=installment_applied,
        credit_entry_amount=credit_entry_amount,
        credit_entry_type=credit_entry_type,
        credit_consumed=credit_consumed,
        invoice_amount=invoice.amount,
    )
    return DepositResult(
        invoice=invoice,
        allocation=allocation,
        credit_balance=credit_balance,
        remaining_installments=remaining_installments,
        warning=warning,
    )


@pytest.fixture
def patch(monkeypatch: pytest.MonkeyPatch):
    def _patch(proof=None, result=None):
        monkeypatch.setattr(
            actions,
            "validate_and_create_proof_of_payment",
            MagicMock(side_effect=lambda *args, **kwargs: proof),
        )
        monkeypatch.setattr(
            actions,
            "register_student_deposit",
            MagicMock(side_effect=lambda *args, **kwargs: result),
        )

    return _patch


def test_no_auth(client):
    url = reverse_lazy("payments:academy_user_deposit")
    response = client.post(url, headers={"Academy": 1})
    json = response.json()
    assert "Authentication credentials were not provided" in json.get("detail", "")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_success_returns_201_with_rich_response(bc: Breathecode, client, patch):
    utc_now = bc.datetime.now()
    model = bc.database.create(
        user=1,
        role=1,
        capability="crud_subscription",
        profile_academy=1,
        invoice=1,
        plan_financing={
            "plan_expires_at": utc_now,
            "valid_until": utc_now,
            "next_payment_at": utc_now,
        },
        currency=1,
        academy=1,
    )
    result = _make_deposit_result(model.invoice, installment_applied=True, credit_balance=0.0, remaining_installments=1)
    proof = MagicMock()
    patch(proof=proof, result=result)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:academy_user_deposit")
    response = client.post(
        url,
        headers={"Academy": 1},
        data={
            "plan_financing": model.plan_financing.id,
            "amount": 1200,
            "payment_method": 1,
            "reference": "REF-123",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # top-level keys
    assert "invoice" in data
    assert "installment_applied" in data
    assert "credit_entry" in data
    assert "credit_balance" in data
    assert "remaining_installments" in data
    assert "warning" in data

    assert data["invoice"]["id"] == model.invoice.id
    assert data["installment_applied"] is True
    assert data["credit_entry"] is None
    assert data["credit_balance"] == 0.0
    assert data["remaining_installments"] == 1
    assert data["warning"] is None

    assert actions.validate_and_create_proof_of_payment.called
    assert actions.register_student_deposit.called
    args = actions.register_student_deposit.call_args[0]
    assert isinstance(args[0], Request)
    assert args[1] is proof
    assert args[2] == 1
    assert args[3] == "en"


def test_response_includes_credit_entry_when_overpayment(bc: Breathecode, client, patch):
    """The API response must include credit_entry when the deposit creates a ledger entry."""
    utc_now = bc.datetime.now()
    model = bc.database.create(
        user=1,
        role=1,
        capability="crud_subscription",
        profile_academy=1,
        invoice=1,
        plan_financing={
            "plan_expires_at": utc_now,
            "valid_until": utc_now,
            "next_payment_at": utc_now,
        },
        currency=1,
        academy=1,
    )
    result = _make_deposit_result(
        model.invoice,
        installment_applied=True,
        credit_entry_amount=300.0,
        credit_entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        credit_balance=300.0,
        remaining_installments=2,
    )
    proof = MagicMock()
    patch(proof=proof, result=result)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:academy_user_deposit")
    response = client.post(
        url,
        headers={"Academy": 1},
        data={"plan_financing": model.plan_financing.id, "amount": 1500, "payment_method": 1},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["installment_applied"] is True
    assert data["credit_entry"] == {"amount": 300.0, "entry_type": "CREDIT_ADDED"}
    assert data["credit_balance"] == 300.0
    assert data["remaining_installments"] == 2
    assert data["warning"] is None


def test_response_includes_warning_when_partial_payment(bc: Breathecode, client, patch):
    """Partial payment: installment_applied=False, warning present, credit_entry present."""
    utc_now = bc.datetime.now()
    model = bc.database.create(
        user=1,
        role=1,
        capability="crud_subscription",
        profile_academy=1,
        invoice=1,
        plan_financing={
            "plan_expires_at": utc_now,
            "valid_until": utc_now,
            "next_payment_at": utc_now,
        },
        currency=1,
        academy=1,
    )
    result = _make_deposit_result(
        model.invoice,
        installment_applied=False,
        credit_entry_amount=200.0,
        credit_entry_type=CreditLedgerEntry.EntryType.CREDIT_ADDED,
        credit_balance=200.0,
        remaining_installments=2,
        warning="Partial payment recorded. Full installment required before 2026-06-01 to avoid cancellation.",
    )
    proof = MagicMock()
    patch(proof=proof, result=result)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:academy_user_deposit")
    response = client.post(
        url,
        headers={"Academy": 1},
        data={"plan_financing": model.plan_financing.id, "amount": 200, "payment_method": 1},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["installment_applied"] is False
    assert data["credit_entry"] == {"amount": 200.0, "entry_type": "CREDIT_ADDED"}
    assert data["credit_balance"] == 200.0
    assert data["warning"] is not None
