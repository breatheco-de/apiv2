"""
Tests for PUT /v1/registry/asset/me/<slug> — owner can set academy_id on global assets.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("breathecode.registry.signals.asset_slug_modified.send_robust", MagicMock())
    yield


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_put_me_assigns_academy_when_asset_has_no_academy(bc: Breathecode, client: APIClient):
    permission = {"codename": "learnpack_create_package"}
    model = bc.database.create(
        user=1,
        permission=permission,
        profile_academy=True,
        role="potato",
        academy=1,
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy": None,
            "owner_id": 1,
            "slug": "owner-global-asset",
            "test_status": "OK",
            "lang": "es",
            "title": "title",
        },
    )
    model.user.user_permissions.add(model.permission)
    client.force_authenticate(user=model.user)

    asset = model.asset
    assert asset.academy_id is None

    url = f"/v1/registry/asset/me/{asset.slug}"
    data = {"id": asset.id, "academy_id": 1, "title": "updated"}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    asset.refresh_from_db()
    assert asset.academy_id == 1
    assert asset.title == "updated"


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_put_me_academy_id_rejected_when_not_academy_member(bc: Breathecode, client: APIClient):
    permission = {"codename": "learnpack_create_package"}
    model = bc.database.create(
        user=1,
        permission=permission,
        profile_academy=True,
        role="potato",
        academy=2,
        asset_category=2,
        asset={
            "category_id": 1,
            "academy": None,
            "owner_id": 1,
            "slug": "owner-global-2",
            "test_status": "OK",
            "lang": "es",
            "title": "title",
        },
    )
    model.user.user_permissions.add(model.permission)
    client.force_authenticate(user=model.user)

    asset = model.asset
    url = f"/v1/registry/asset/me/{asset.slug}"
    data = {"id": asset.id, "academy_id": 2, "title": "x"}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == "not-member-of-academy"
    asset.refresh_from_db()
    assert asset.academy_id is None


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_put_me_academy_id_rejected_when_academy_does_not_exist(bc: Breathecode, client: APIClient):
    permission = {"codename": "learnpack_create_package"}
    model = bc.database.create(
        user=1,
        permission=permission,
        profile_academy=True,
        role="potato",
        academy=1,
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy": None,
            "owner_id": 1,
            "slug": "owner-global-3",
            "test_status": "OK",
            "lang": "es",
            "title": "title",
        },
    )
    model.user.user_permissions.add(model.permission)
    client.force_authenticate(user=model.user)

    asset = model.asset
    url = f"/v1/registry/asset/me/{asset.slug}"
    data = {"id": asset.id, "academy_id": 99999, "title": "x"}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == "academy-not-found"


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_put_me_cannot_change_existing_academy(bc: Breathecode, client: APIClient):
    permission = {"codename": "learnpack_create_package"}
    model = bc.database.create(
        user=1,
        permission=permission,
        profile_academy=True,
        role="potato",
        academy=2,
        asset_category=2,
        asset={
            "category_id": 1,
            "academy_id": 1,
            "owner_id": 1,
            "slug": "owned-academy-asset",
            "test_status": "OK",
            "lang": "es",
            "title": "title",
        },
    )
    model.user.user_permissions.add(model.permission)
    client.force_authenticate(user=model.user)

    asset = model.asset
    url = f"/v1/registry/asset/me/{asset.slug}"
    data = {"id": asset.id, "academy_id": 2, "title": "x"}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("detail") == "asset-academy-locked"
