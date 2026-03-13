"""
Tests for POST academy/user/consumable (AcademyGrantConsumableView).
Staff grant consumables: requires crud_consumable, proof (file or reference), non-card/non-crypto payment_method.
"""

from unittest.mock import MagicMock

import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.request import Request

from breathecode.payments import actions
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


@pytest.fixture
def patch(monkeypatch: pytest.MonkeyPatch):
    """Patch proof creation and grant action; grant returns invoice."""

    def _patch(proof=None, invoice=None):
        monkeypatch.setattr(
            actions,
            "validate_and_create_proof_of_payment",
            MagicMock(side_effect=lambda *args, **kwargs: proof),
        )
        monkeypatch.setattr(
            actions,
            "grant_consumables_for_user",
            MagicMock(side_effect=lambda *args, **kwargs: invoice),
        )

    return _patch


def test_no_auth(client):
    url = reverse_lazy("payments:academy_user_consumable")
    response = client.post(url, headers={"Academy": 1})
    json = response.json()
    assert "Authentication credentials were not provided" in json.get("detail", "")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_success_returns_201_and_invoice(bc: Breathecode, client, patch):
    """POST with auth and capability returns 201 and serialized invoice."""
    model = bc.database.create(
        user=1,
        role=1,
        capability="crud_consumable",
        profile_academy=1,
        invoice=1,
        currency=1,
    )
    proof = MagicMock()
    patch(proof=proof, invoice=model.invoice)
    client.force_authenticate(user=model.user)

    url = reverse_lazy("payments:academy_user_consumable")
    response = client.post(
        url,
        headers={"Academy": 1},
        data={
            "user": model.user.id,
            "service": 1,
            "how_many": 2,
            "payment_method": 1,
            "reference": "REF-123",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    json = response.json()
    assert json.get("id") == model.invoice.id
    assert actions.validate_and_create_proof_of_payment.called
    assert actions.grant_consumables_for_user.called
    args = actions.grant_consumables_for_user.call_args[0]
    assert isinstance(args[0], Request)
    assert args[1] is proof
    assert args[2] == 1  # academy_id
    assert args[3] == "en"  # lang
