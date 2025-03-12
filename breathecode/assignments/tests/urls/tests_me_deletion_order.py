"""
Test /me/deletion_order
"""

import json
import re

import pytest
import capyc.pytest as capyc
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


def get_deletion_order_serializer(deletion_order, data={}):
    return {
        "user": {
            "id": deletion_order.user.id,
            "first_name": deletion_order.user.first_name,
            "last_name": deletion_order.user.last_name,
        },
        "id": deletion_order.id,
        "repository_name": deletion_order.repository_name,
        "repository_user": deletion_order.repository_user,
        "status": deletion_order.status,
        "status_text": deletion_order.status_text,
        "starts_transferring_at": deletion_order.starts_transferring_at,
        **data,
    }


# When: no auth
# Then: response 401
def test_no_auth(client: capyc.Client):
    url = reverse_lazy("assignments:me_deletion_order")
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# When: No repository deletion orders
# Then: response 200
def test_no_deletion_orders(database: capyc.Database, client: capyc.Client):

    model = database.create(user=1)
    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:me_deletion_order")

    response = client.get(url)
    json = response.json()

    expected = []

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


# When: There is one deletion order
# Then: response 200
def test_one_transferring_deletion_order(database: capyc.Database, client: capyc.Client):

    model = database.create(user=1)
    client.force_authenticate(model.user)

    deletion_model = database.create(repository_deletion_order={"user": model.user, "status": "PENDING"})

    url = reverse_lazy("assignments:me_deletion_order")

    response = client.get(url)
    json = response.json()

    order_transferring = deletion_model.repository_deletion_order

    expected = [get_deletion_order_serializer(order_transferring)]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


def test_one_transferring_deletion_order_querying_status(database: capyc.Database, client: capyc.Client):

    model = database.create(user=1)
    client.force_authenticate(model.user)

    deletion_model = database.create(
        repository_deletion_order=[
            {"user": model.user, "status": "PENDING"},
            {"user": model.user, "status": "TRANSFERRING"},
        ]
    )

    url = reverse_lazy("assignments:me_deletion_order") + "?status=transferring"

    response = client.get(url)
    json = response.json()

    order_transferring = deletion_model.repository_deletion_order[1]

    starts_transferring_at = re.sub(r"\+00:00$", "Z", order_transferring.starts_transferring_at.isoformat())

    expected = [
        get_deletion_order_serializer(order_transferring, data={"starts_transferring_at": starts_transferring_at})
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
