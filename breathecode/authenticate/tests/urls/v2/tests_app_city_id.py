from typing import Any, Callable

import capyc.pytest as capy
import linked_services.pytest as linked_services
import pytest
from django.http import JsonResponse
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.authenticate.serializers import CapyAppCitySerializer


@pytest.fixture(autouse=True)
def setup(db):
    yield


@pytest.fixture
def expected(monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
    obj = {
        "slug": fake.slug(),
        "name": fake.name(),
        "description": fake.text(),
    }

    def m(self, **kwargs):
        return JsonResponse({**obj, **kwargs}, status=200)

    monkeypatch.setattr(CapyAppCitySerializer, "get", m)

    yield {
        **obj,
        "id": 1,
    }


def test_no_authorization_header(client: capy.Client):
    url = reverse_lazy("v2:authenticate:app_city_id", kwargs={"city_id": 1})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "no-authorization-header", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_authorization_header(client: capy.Client):
    url = reverse_lazy("v2:authenticate:app_city_id", kwargs={"city_id": 1})
    response = client.get(url, headers={"Authorization": "Bearer 1234"})

    json = response.json()
    expected = {"detail": "unknown-auth-schema", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_location_url(
    database: capy.Database,
    client: capy.Client,
    service: linked_services.Service,
    get_app_signature: Callable[[Any], dict[str, Any]],
    expected: dict[str, str],
):
    url = reverse_lazy("v2:authenticate:app_city_id", kwargs={"city_id": 1})

    model = database.create(
        app={
            "require_an_agreement": False,
            "slug": "rigobot",
            **get_app_signature(),
        },
    )

    service.sign_jwt(client, model.app)
    response = client.get(url)

    json = response.json()

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
