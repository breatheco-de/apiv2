"""
Test cases for /user
"""

import pytest
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def test_user_without_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:app_webhook")
    response = client.post(url, {}, format="json")

    json = response.json()
    expected = {
        "detail": "no-authorization-header",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def db_item(data={}):
    return {
        "id": 0,
        "app_id": 0,
        "type": "unknown",
        "user_id": 0,
        "external_id": None,
        "url": None,
        "data": {},
        "processed": False,
        "attempts": 0,
        "status": "PENDING",
        "status_text": None,
        **data,
    }


@pytest.mark.parametrize(
    "how_many,webhook_id,webhook_type,user_id,data",
    [
        (1, None, None, None, None),
        (2, 1, "user.created", 1, {"random": "data"}),
        (
            2,
            1,
            "user.updated",
            1,
            [
                {
                    "random": "data1",
                },
                {
                    "random": "data2",
                },
            ],
        ),
    ],
)
def test_webhook_not_registered(bc: Breathecode, client: APIClient, how_many, webhook_id, webhook_type, user_id, data):
    app = {"require_an_agreement": False}
    model = bc.database.create(user=2, app=app)

    input = {
        "id": webhook_id,
        "data": data,
        "type": webhook_type,
    }
    if how_many != 1:
        input = [
            input,
            {
                "id": webhook_id + 1 if webhook_id else None,
                "data": data,
                "type": webhook_type,
            },
        ]

    bc.request.sign_jwt_link(model.app, user_id, client=client)

    url = reverse_lazy("authenticate:app_webhook")
    response = client.post(url, input, format="json")

    assert response.content == b""
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = [
        db_item(
            {
                "id": 1,
                "app_id": 1,
                "user_id": user_id,
                "status": "PENDING",
                "external_id": webhook_id,
                "type": webhook_type or "unknown",
                "data": data,
            }
        ),
    ]
    if how_many != 1:
        db += [
            db_item(
                {
                    "id": 2,
                    "app_id": 1,
                    "user_id": user_id,
                    "status": "PENDING",
                    "external_id": webhook_id + 1 if webhook_id else None,
                    "type": webhook_type or "unknown",
                    "data": data,
                }
            ),
        ]
    assert bc.database.list_of("linked_services.FirstPartyWebhookLog") == db


@pytest.mark.parametrize(
    "how_many,webhook_id,webhook_type,user_id,data",
    [
        # (1, None, None, None, None),
        (2, 1, "user.created", 1, {"random": "data"}),
        (
            2,
            1,
            "user.updated",
            1,
            [
                {
                    "random": "data1",
                },
                {
                    "random": "data2",
                },
            ],
        ),
    ],
)
def test_webhook_registered(bc: Breathecode, client: APIClient, how_many, webhook_id, webhook_type, user_id, data):
    app = {"require_an_agreement": False}
    first_party_webhook_log = {
        "external_id": webhook_id,
        "type": webhook_type,
        "user_id": user_id,
    }
    if how_many != 1:
        first_party_webhook_log = [
            first_party_webhook_log,
            {
                "external_id": webhook_id + 1 if webhook_id else None,
                "type": webhook_type,
                "user_id": user_id,
            },
        ]
    model = bc.database.create(user=2, app=app, first_party_webhook_log=first_party_webhook_log)

    input = {
        "id": webhook_id,
        "data": data,
        "type": webhook_type,
    }
    if how_many != 1:
        input = [
            input,
            {
                "id": webhook_id + 1 if webhook_id else None,
                "data": data,
                "type": webhook_type,
            },
        ]

    bc.request.sign_jwt_link(model.app, user_id, client=client)

    url = reverse_lazy("authenticate:app_webhook")
    response = client.post(url, input, format="json")

    assert response.content == b""
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db = [
        db_item(
            {
                "id": 1,
                "app_id": 1,
                "user_id": user_id,
                "status": "PENDING",
                "external_id": webhook_id,
                "type": webhook_type or "unknown",
                "data": data,
            }
        ),
    ]
    if how_many != 1:
        db += [
            db_item(
                {
                    "id": 2,
                    "app_id": 1,
                    "user_id": user_id,
                    "status": "PENDING",
                    "external_id": webhook_id + 1 if webhook_id else None,
                    "type": webhook_type or "unknown",
                    "data": data,
                }
            ),
        ]
    assert bc.database.list_of("linked_services.FirstPartyWebhookLog") == db
