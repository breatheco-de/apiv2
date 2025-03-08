"""
Test cases for /user
"""

from typing import Callable
from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.response import Response

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    from linked_services.django.actions import reset_app_cache

    reset_app_cache()
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())
    yield


@pytest.fixture(autouse=True)
def patch_get_user(monkeypatch: pytest.MonkeyPatch):

    def patch(user):
        monkeypatch.setattr("breathecode.payments.views.AppConsumableView.get_user", MagicMock(return_value=user))

    yield patch


@pytest.fixture(autouse=True)
def endpoint_mock(monkeypatch: pytest.MonkeyPatch):
    m = []

    def get(request, *args, **kwargs):
        m.append((args, kwargs))
        return Response({"mocked": "ok"}, status=status.HTTP_200_OK)

    monkeypatch.setattr(
        "breathecode.payments.views.MeConsumableView.get",
        MagicMock(side_effect=get),
    )

    yield m


def test_no_auth(bc: Breathecode, client: capy.Client):
    url = reverse_lazy("payments:app_service_consumable")
    response = client.get(url)

    json = response.json()
    expected = {
        "detail": "no-authorization-header",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_not_provided(
    bc: Breathecode,
    client: capy.Client,
    sign_jwt_link: Callable[..., None],
    patch_get_user: Callable[..., None],
    endpoint_mock: list[tuple[tuple, dict]],
):
    app = {"require_an_agreement": False, "slug": "rigobot"}
    model = bc.database.create(
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
    )

    mock = endpoint_mock
    patch_get_user(None)
    sign_jwt_link(client, model.app, 1)

    url = reverse_lazy("payments:app_service_consumable")
    response = client.get(url)

    json = response.json()
    expected = {
        "detail": "User not provided",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert mock == []


def test_forward_request(
    bc: Breathecode,
    client: capy.Client,
    sign_jwt_link: Callable[..., None],
    patch_get_user: Callable[..., None],
    endpoint_mock: list[tuple[tuple, dict]],
):
    app = {"require_an_agreement": False, "slug": "rigobot"}
    model = bc.database.create(
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
    )

    sign_jwt_link(client, model.app, 1)
    patch_get_user(model.user)
    mock = endpoint_mock

    url = reverse_lazy("payments:app_service_consumable")
    response = client.get(url)

    json = response.json()
    expected = {"mocked": "ok"}

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert mock == [
        ((), {}),
    ]
