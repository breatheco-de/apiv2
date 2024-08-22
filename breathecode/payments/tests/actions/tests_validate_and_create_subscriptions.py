"""
Test /answer
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

import pytest
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from breathecode.payments.actions import validate_and_create_subscriptions
from breathecode.payments.tasks import build_plan_financing
from capyc.rest_framework import pytest as capy
from capyc.rest_framework.exceptions import ValidationException

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr("breathecode.payments.tasks.build_plan_financing.delay", MagicMock())


def get_request(data, headers={}, user=None) -> WSGIRequest:
    factory = APIRequestFactory()
    request = factory.post("/they-killed-kenny", data, headers=headers)
    request.data = data

    if user:
        force_authenticate(request, user=user)

    return request


def serialize_proof_of_payment(data={}):
    return {
        "confirmation_image_url": None,
        "created_by_id": 0,
        "id": 0,
        "provided_payment_details": "",
        "reference": None,
        "status": "PENDING",
        **data,
    }


def serialize_bag(data={}):
    return {
        "academy_id": 1,
        "amount_per_half": 0.0,
        "amount_per_month": 0.0,
        "amount_per_quarter": 0.0,
        "amount_per_year": 0.0,
        "chosen_period": "NO_SET",
        "currency_id": 1,
        "expires_at": None,
        "how_many_installments": 1,
        "id": 1,
        "is_recurrent": True,
        "status": "PAID",
        "token": None,
        "type": "BAG",
        "user_id": 1,
        "was_delivered": False,
        **data,
    }


def serialize_invoice(data={}):
    return {
        "academy_id": 1,
        "amount": 1.0,
        "bag_id": 1,
        "currency_id": 1,
        "externally_managed": True,
        "id": 1,
        "paid_at": None,
        "payment_method_id": None,
        "proof_id": 1,
        "refund_stripe_id": None,
        "refunded_at": None,
        "status": "FULFILLED",
        "stripe_id": None,
        "user_id": 1,
        **data,
    }


@pytest.mark.parametrize("is_request", [True, False])
def test_no_data(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    data = {}
    academy = 1
    model = database.create(user=1, proof_of_payment=1)

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="exactly-one-plan-must-be-provided"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_no_financing_option(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    model = database.create(user=1, proof_of_payment=1, plan={"time_of_life": None, "time_of_life_unit": None})
    data = {"plans": [model.plan.slug]}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="financing-option-not-found"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_no_academy(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    model = database.create(
        user=1,
        proof_of_payment=1,
        plan={"time_of_life": None, "time_of_life_unit": None},
        financing_option={"how_many_months": 1},
    )
    data = {"plans": [model.plan.slug]}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="academy-not-found"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_no_user(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    model = database.create(
        user=1,
        proof_of_payment=1,
        plan={"time_of_life": None, "time_of_life_unit": None},
        financing_option={"how_many_months": 1},
        academy=1,
        city=1,
        country=1,
    )
    data = {"plans": [model.plan.slug]}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="user-must-be-provided"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_no_payment_method(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    model = database.create(
        user=1,
        proof_of_payment=1,
        plan={"time_of_life": None, "time_of_life_unit": None},
        financing_option={"how_many_months": 1},
        academy=1,
        city=1,
        country=1,
        payment_method=1,
    )
    data = {"plans": [model.plan.slug], "user": model.user.id}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="payment-method-not-provided"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_plan_already_exists(database: capy.Database, format: capy.Format, is_request: bool, utc_now: datetime) -> None:
    model = database.create(
        user=1,
        proof_of_payment=1,
        plan={"time_of_life": None, "time_of_life_unit": None},
        financing_option={"how_many_months": 1},
        academy=1,
        city=1,
        country=1,
        payment_method=1,
        plan_financing={
            "valid_until": utc_now + timedelta(days=30),
            "plan_expires_at": utc_now + timedelta(days=30),
            "monthly_price": 100,
        },
    )
    data = {"plans": [model.plan.slug], "user": model.user.id, "payment_method": 1}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="user-already-has-valid-subscription"):
        validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == []
    assert database.list_of("payments.Invoice") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
@pytest.mark.parametrize("field", ["id", "username", "email"])
def test_schedule_plan_financing(
    database: capy.Database, format: capy.Format, is_request: bool, field: str, utc_now: datetime
) -> None:
    model = database.create(
        user=1,
        proof_of_payment=1,
        plan={"time_of_life": None, "time_of_life_unit": None},
        financing_option={"how_many_months": 1},
        academy=1,
        city=1,
        country=1,
        payment_method=1,
    )
    data = {"plans": [model.plan.slug], "user": getattr(model.user, field), "payment_method": 1}
    academy = 1

    if is_request:
        data = get_request(data, user=model.user)

    result = validate_and_create_subscriptions(data, model.user, model.proof_of_payment, academy, "en")

    assert database.list_of("payments.Bag") == [
        serialize_bag(),
    ]
    assert database.list_of("payments.Invoice") == [
        serialize_invoice(
            data={
                "id": 1,
                "paid_at": utc_now,
                "payment_method_id": 1,
            }
        ),
    ]
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "status": "PENDING",
            }
        ),
    ]

    assert build_plan_financing.delay.call_args_list == [call(1, 1, conversion_info=None)]

    assert len(result) == 2

    assert result[0].__module__ == "breathecode.payments.models"
    assert result[0].__class__.__name__ == "Invoice"
    assert result[0].id == 1

    assert result[1] == []
