"""
Test /answer
"""

from unittest.mock import MagicMock, call

import pytest
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from breathecode.payments.actions import validate_and_create_proof_of_payment
from breathecode.payments.tasks import set_proof_of_payment_confirmation_url
from capyc.rest_framework import pytest as capy
from capyc.rest_framework.exceptions import ValidationException

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(set_proof_of_payment_confirmation_url, "delay", MagicMock())


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
        "reference": "",
        "status": "PENDING",
        **data,
    }


@pytest.mark.parametrize("is_request", [True, False])
def test_no_data(database: capy.Database, format: capy.Format, is_request: bool) -> None:
    data = {}
    academy = 1
    model = database.create(user=1)

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="at-least-one-of-file-or-reference-must-be-provided"):
        validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == []
    assert database.list_of("payments.ProofOfPayment") == []
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_generate_proof_with_reference(database: capy.Database, fake: capy.Fake, is_request: bool) -> None:
    slug = fake.slug()
    data = {"reference": slug}
    academy = 1
    model = database.create(user=1)

    if is_request:
        data = get_request(data, user=model.user)

    validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "reference": slug,
                "status": "DONE",
            }
        ),
    ]
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_generate_proof_with_reference_and_details(database: capy.Database, fake: capy.Fake, is_request: bool) -> None:
    slug = fake.slug()
    provided_payment_details = fake.text()[:255]
    data = {"reference": slug, "provided_payment_details": provided_payment_details}
    academy = 1
    model = database.create(user=1)

    if is_request:
        data = get_request(data, user=model.user)

    validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == []
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "reference": slug,
                "status": "DONE",
                "provided_payment_details": provided_payment_details,
            }
        ),
    ]
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
def test_file_not_found(database: capy.Database, fake: capy.Fake, is_request: bool) -> None:
    slug = fake.slug()
    data = {"file": 1}
    academy = 1
    model = database.create(user=1)

    if is_request:
        data = get_request(data, user=model.user)

    with pytest.raises(ValidationException, match="invalid-file-id"):
        validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == []
    assert database.list_of("payments.ProofOfPayment") == []
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == []


@pytest.mark.parametrize("is_request", [True, False])
@pytest.mark.parametrize("extra", [{}, {"academy": 1, "country": 1, "city": 1}])
def test_generate_proof_with_file(database: capy.Database, is_request: bool, format: capy.Format, extra: dict) -> None:
    data = {"file": 1}
    academy = 1
    model = database.create(user=1, file=1, **extra)

    if is_request:
        data = get_request(data, user=model.user)

    validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == [
        {
            **format.to_obj_repr(model.file),
            "status": "TRANSFERRING",
        }
    ]
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "reference": None,
                "status": "PENDING",
                "provided_payment_details": "",
            }
        ),
    ]
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == [call(1, 1)]


@pytest.mark.parametrize("is_request", [True, False])
@pytest.mark.parametrize("extra", [{}, {"academy": 1, "country": 1, "city": 1}])
def test_generate_proof_with_file_and_details(
    database: capy.Database, fake: capy.Fake, is_request: bool, format: capy.Format, extra: dict
) -> None:
    provided_payment_details = fake.text()[:255]
    data = {"file": 1, "provided_payment_details": provided_payment_details}
    academy = 1
    model = database.create(user=1, file=1, **extra)

    if is_request:
        data = get_request(data, user=model.user)

    validate_and_create_proof_of_payment(data, model.user, academy, "en")

    assert database.list_of("media.File") == [
        {
            **format.to_obj_repr(model.file),
            "status": "TRANSFERRING",
        }
    ]
    assert database.list_of("payments.ProofOfPayment") == [
        serialize_proof_of_payment(
            data={
                "id": 1,
                "created_by_id": 1,
                "reference": None,
                "status": "PENDING",
                "provided_payment_details": provided_payment_details,
            }
        ),
    ]
    assert set_proof_of_payment_confirmation_url.delay.call_args_list == [call(1, 1)]
