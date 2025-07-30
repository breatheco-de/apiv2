from unittest.mock import MagicMock

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.registry import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.tests.mixins.legacy import LegacyAPITestCase


def get_asset_category(category):
    return {"id": category.id, "slug": category.slug, "title": category.title}


def get_serializer(bc: Breathecode, asset, asset_category=None, data={}):
    return {
        "assessment": asset.assessment,
        "asset_type": asset.asset_type,
        "enable_table_of_content": asset.enable_table_of_content,
        "interactive": asset.interactive,
        "author": asset.author,
        "authors_username": None,
        "category": get_asset_category(asset_category) if asset_category else None,
        "cleaning_status": asset.cleaning_status,
        "cleaning_status_details": None,
        "clusters": [],
        "assets_related": [],
        "previous_versions": [],
        "description": None,
        "difficulty": None,
        "readme_updated_at": None,
        "duration": None,
        "external": False,
        "gitpod": False,
        "graded": False,
        "id": asset.id,
        "intro_video_url": None,
        "is_seo_tracked": True,
        "lang": asset.lang,
        "feature": False,
        "last_synch_at": None,
        "last_test_at": None,
        "last_cleaning_at": None,
        "last_seo_scan_at": None,
        "learnpack_deploy_url": None,
        "optimization_rating": None,
        "owner": None,
        "preview": None,
        "published_at": None,
        "readme_url": None,
        "requirements": None,
        "seo_json_status": None,
        "seo_keywords": [],
        "slug": asset.slug,
        "solution_video_url": None,
        "solution_url": None,
        "status": "NOT_STARTED",
        "status_text": None,
        "sync_status": None,
        "technologies": [],
        "test_status": None,
        "title": asset.title,
        "translations": {},
        "url": None,
        "visibility": "PUBLIC",
        "allow_contributions": asset.allow_contributions,
        "academy": asset.academy.id if asset.academy else None,
        "config": asset.config,
        "flag_seed": asset.flag_seed,
        "created_at": bc.datetime.to_iso_string(asset.created_at),
        "updated_at": bc.datetime.to_iso_string(asset.updated_at),
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("breathecode.registry.signals.asset_slug_modified.send_robust", MagicMock())
    yield


def test_no_auth(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": "model_slug"})
    response = client.get(url)
    json = response.json()

    assert json == {
        "detail": "Authentication credentials were not provided.",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("registry.Asset") == []


def test_no_capability(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": "model_slug"})
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = {
        "status_code": 403,
        "detail": "You (user: 1) don't have this capability: read_asset for academy 1",
    }

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert bc.database.list_of("registry.Asset") == []


def test_no_consumables(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": "model_slug"})
    model = bc.database.create(user=1, profile_academy=1, role=1, capability="read_asset")
    client.force_authenticate(user=model.user)

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = {
        "detail": "asset-not-found",
        "status_code": 404,
    }

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("registry.Asset") == []


def test_no_asset(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    model = bc.database.create(
        user=1, profile_academy=1, role=1, capability="read_asset", service={"consumer": "READ_LESSON"}, consumable=1
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": "model_slug"})

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = {
        "detail": "asset-not-found",
        "status_code": 404,
    }

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("registry.Asset") == []


def test_with_asset(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    model = bc.database.create(
        user=1,
        profile_academy=1,
        role=1,
        capability="read_asset",
        service={"consumer": "READ_LESSON"},
        consumable=1,
        asset={"allow_contributions": True},
        asset_category=1,
        academy=1,
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": model.asset.slug})

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = get_serializer(bc, model.asset, asset_category=model.asset_category)

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


# Given: A no SAAS student who has paid
# When: auth
# Then: response 200
@pytest.mark.parametrize(
    "cohort_user",
    [
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "GRADUATED",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "GRADUATED",
        },
    ],
)
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
def test_with_asset__no_saas__finantial_status_no_late(
    bc: Breathecode, client: APIClient, academy, cohort, cohort_user
):
    """Test /certificate without auth"""
    model = bc.database.create(
        user=1,
        profile_academy=1,
        role=1,
        capability="read_asset",
        service={"consumer": "READ_LESSON"},
        consumable=1,
        asset={"allow_contributions": True},
        asset_category=1,
        academy=academy,
        cohort=cohort,
        cohort_user=cohort_user,
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": model.asset.slug})

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = get_serializer(bc, model.asset, asset_category=model.asset_category)

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


# Given: A no SAAS student who hasn't paid
# When: auth
# Then: response 402
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
def test_with_asset__no_saas__finantial_status_late(bc: Breathecode, client: APIClient, academy, cohort, fake):
    """Test /certificate without auth"""
    cohort_user = {"finantial_status": "LATE", "educational_status": "ACTIVE"}
    slug = fake.slug()
    model = bc.database.create(
        user=1,
        profile_academy=1,
        role=1,
        capability="read_asset",
        service={"consumer": "READ_LESSON"},
        consumable=1,
        asset={"slug": slug, "allow_contributions": True},
        syllabus_version={
            "json": {
                "x": slug,
            },
        },
        asset_category=1,
        academy=academy,
        cohort=cohort,
        cohort_user=cohort_user,
    )
    client.force_authenticate(user=model.user)
    url = reverse_lazy("v2:registry:academy_asset_slug", kwargs={"asset_slug": model.asset.slug})

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = {"detail": "cohort-user-status-later", "status_code": 402}

    assert json == expected
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]
