import random
from datetime import timedelta
from unittest.mock import MagicMock

import capyc.pytest as capy
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
def patch(db, monkeypatch: pytest.MonkeyPatch):
    def wrapper(proof=None, invoices=[], coupons=[]):
        def x(*args, **kwargs):
            return invoices, coupons

        monkeypatch.setattr(
            actions, "validate_and_create_proof_of_payment", MagicMock(side_effect=lambda *args, **kwargs: proof)
        )
        monkeypatch.setattr(actions, "validate_and_create_subscriptions", MagicMock(side_effect=x))

    yield wrapper


def random_duration():
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def serialize_invoice(invoice, currency, user, data={}):
    return {
        "id": invoice.id,
        "amount": invoice.amount,
        "currency": {
            "code": currency.code,
            "name": currency.name,
        },
        "paid_at": invoice.paid_at.isoformat().replace("+00:00", "Z"),
        "status": str(invoice.status),
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        **data,
    }


def serialize_coupon(coupon, data={}):
    return {
        "auto": coupon.auto,
        "discount_type": str(coupon.discount_type),
        "discount_value": coupon.discount_value,
        "expires_at": coupon.expires_at,
        "offered_at": coupon.offered_at.isoformat().replace("+00:00", "Z"),
        "referral_type": str(coupon.referral_type),
        "referral_value": coupon.referral_value,
        "slug": coupon.slug,
        **data,
    }


def test_no_auth(client: capy.Client):
    url = reverse_lazy("payments:academy_plan_slug_subscription", kwargs={"plan_slug": "my-service"})

    response = client.post(url, headers={"Academy": 1})

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_proxy_all(bc: Breathecode, client: capy.Client, fake, patch):
    url = reverse_lazy("payments:academy_plan_slug_subscription", kwargs={"plan_slug": "my-service"})

    model = bc.database.create(
        user=1, role=1, capability="crud_subscription", profile_academy=1, invoice=1, coupon=(2, {"discount_value": 10})
    )
    slug = fake.slug()
    patch(slug, model.invoice, model.coupon)
    client.force_authenticate(user=model.user)

    response = client.post(url, headers={"Academy": 1})

    json = response.json()
    expected = {
        **serialize_invoice(model.invoice, model.currency, model.user),
        "coupons": [
            serialize_coupon(model.coupon[0]),
            serialize_coupon(model.coupon[1]),
        ],
    }

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    assert len(actions.validate_and_create_proof_of_payment.call_args_list) == 1
    assert len(actions.validate_and_create_subscriptions.call_args_list) == 1

    args, kwargs = actions.validate_and_create_proof_of_payment.call_args_list[0]

    assert isinstance(args[0], Request)
    assert args[1:] == (model.user, 1, "en")
    assert kwargs == {}

    args, kwargs = actions.validate_and_create_subscriptions.call_args_list[0]
    assert isinstance(args[0], Request)
    assert args[1:] == (model.user, slug, 1, "en")
    assert kwargs == {}
