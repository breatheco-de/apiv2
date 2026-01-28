import pytest
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.registry.models import Asset
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


def test_put_asset_name_without_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("registry:academy_asset_slug_name", kwargs={"asset_slug": "some-asset"})

    response = client.put(url, {"title": "New name"}, format="json", HTTP_ACADEMY=1)
    json = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert json == {
        "detail": "Authentication credentials were not provided.",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }


def test_put_asset_name_without_capability(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)
    url = reverse_lazy("registry:academy_asset_slug_name", kwargs={"asset_slug": "some-asset"})

    response = client.put(url, {"title": "New name"}, format="json", HTTP_ACADEMY=1)
    json = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert json == {
        "status_code": 403,
        "detail": "You (user: 1) don't have this capability: crud_asset for academy 1",
    }


def test_put_asset_name_missing_title(bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=1,
        academy=1,
        role=1,
        capability="crud_asset",
        profile_academy=1,
        asset_category={"lang": "us"},
        asset={"academy_id": 1, "category_id": 1, "slug": "asset-slug", "lang": "us", "title": "Old title"},
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("registry:academy_asset_slug_name", kwargs={"asset_slug": model.asset.slug})

    response = client.put(url, {}, format="json", HTTP_ACADEMY=1)
    json = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json["detail"] == "missing-title"
    assert json["status_code"] == 400


def test_put_asset_name_not_found(bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=1,
        academy=1,
        role=1,
        capability="crud_asset",
        profile_academy=1,
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("registry:academy_asset_slug_name", kwargs={"asset_slug": "missing-asset"})

    response = client.put(url, {"title": "New name"}, format="json", HTTP_ACADEMY=1)
    json = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert json["detail"] == "asset-not-found"
    assert json["status_code"] == 404


def test_put_asset_name_success(bc: Breathecode, client: APIClient):
    model = bc.database.create(
        user=1,
        academy=1,
        role=1,
        capability="crud_asset",
        profile_academy=1,
        asset_category={"lang": "us"},
        asset={"academy_id": 1, "category_id": 1, "slug": "asset-slug", "lang": "us", "title": "Old title"},
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("registry:academy_asset_slug_name", kwargs={"asset_slug": model.asset.slug})

    response = client.put(url, {"title": "New title"}, format="json", HTTP_ACADEMY=1)
    json = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert json["title"] == "New title"
    assert json["slug"] == model.asset.slug

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.title == "New title"
