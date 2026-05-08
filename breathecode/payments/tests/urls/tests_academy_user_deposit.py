from unittest.mock import MagicMock

import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.request import Request

from breathecode.payments import actions
from breathecode.payments.models import StudentDeposit
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


@pytest.fixture
def patch(monkeypatch: pytest.MonkeyPatch):
    def _patch(proof=None, deposit=None):
        monkeypatch.setattr(
            actions,
            "validate_and_create_proof_of_payment",
            MagicMock(side_effect=lambda *args, **kwargs: proof),
        )
        monkeypatch.setattr(
            actions,
            "register_student_deposit",
            MagicMock(side_effect=lambda *args, **kwargs: deposit),
        )

    return _patch


def test_no_auth(client):
    url = reverse_lazy("payments:academy_user_deposit")
    response = client.post(url, headers={"Academy": 1})
    json = response.json()
    assert "Authentication credentials were not provided" in json.get("detail", "")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_success_returns_201_and_deposit(bc: Breathecode, client, patch):
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
    deposit = StudentDeposit.objects.create(
        user=model.user,
        academy=model.academy,
        invoice=model.invoice,
        plan_financing=model.plan_financing,
        amount=1200,
        currency=model.currency,
        status=StudentDeposit.Status.APPLIED,
        applied_at=utc_now,
    )
    proof = MagicMock()
    patch(proof=proof, deposit=deposit)
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
    json = response.json()
    assert json["id"] == deposit.id
    assert json["status"] == deposit.status
    assert actions.validate_and_create_proof_of_payment.called
    assert actions.register_student_deposit.called
    args = actions.register_student_deposit.call_args[0]
    assert isinstance(args[0], Request)
    assert args[1] is proof
    assert args[2] == 1
    assert args[3] == "en"
