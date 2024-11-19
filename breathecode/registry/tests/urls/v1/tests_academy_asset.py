"""
    🔽🔽🔽 Testing Asset Creation without category
"""

from unittest.mock import MagicMock, call, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.registry import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


def database_item(academy, category, data={}):
    return {
        "academy_id": academy.id,
        "learnpack_deploy_url": None,
        "agent": None,
        "assessment_id": None,
        "asset_type": "PROJECT",
        "author_id": None,
        "authors_username": None,
        "category_id": category.id,
        "cleaning_status": "PENDING",
        "cleaning_status_details": None,
        "config": None,
        "delivery_formats": "url",
        "delivery_instructions": None,
        "readme_updated_at": None,
        "delivery_regex_url": None,
        "description": None,
        "difficulty": None,
        "duration": None,
        "external": False,
        "gitpod": False,
        "graded": False,
        "html": None,
        "id": 1,
        "interactive": False,
        "intro_video_url": None,
        "is_seo_tracked": True,
        "lang": None,
        "last_cleaning_at": None,
        "last_seo_scan_at": None,
        "last_synch_at": None,
        "last_test_at": None,
        "optimization_rating": None,
        "owner_id": None,
        "github_commit_hash": None,
        "preview": None,
        "published_at": None,
        "readme": None,
        "readme_raw": None,
        "readme_url": None,
        "requirements": None,
        "seo_json_status": None,
        "slug": "",
        "solution_url": None,
        "solution_video_url": None,
        "status": "NOT_STARTED",
        "status_text": None,
        "sync_status": None,
        "test_status": None,
        "title": "",
        "url": None,
        "visibility": "PUBLIC",
        "with_solutions": False,
        "with_video": False,
        "is_auto_subscribed": True,
        "superseded_by_id": None,
        "enable_table_of_content": True,
        "agent": None,
        "learnpack_deploy_url": None,
        "template_url": None,
        "dependencies": None,
        "preview_in_tutorial": None,
        **data,
    }


def post_serializer(academy, category, data={}):
    translations = {}

    return {
        "academy": {"id": academy.id, "name": academy.name},
        "asset_type": "PROJECT",
        "author": None,
        "category": {
            "id": category.id,
            "slug": category.slug,
            "title": category.title,
        },
        "agent": None,
        "delivery_formats": "url",
        "delivery_instructions": None,
        "delivery_regex_url": None,
        "description": None,
        "difficulty": None,
        "duration": None,
        "external": False,
        "gitpod": False,
        "graded": False,
        "id": academy.id,
        "interactive": False,
        "intro_video_url": None,
        "lang": None,
        "last_synch_at": None,
        "last_test_at": None,
        "owner": None,
        "preview": None,
        "published_at": None,
        "readme_url": None,
        "seo_keywords": [],
        "slug": "",
        "solution_url": None,
        "solution_video_url": None,
        "status": "NOT_STARTED",
        "status_text": None,
        "sync_status": None,
        "technologies": [],
        "test_status": None,
        "title": "model_title",
        "translations": translations,
        "url": None,
        "visibility": "PUBLIC",
        "with_solutions": False,
        "assets_related": [],
        "with_video": False,
        "superseded_by": None,
        "enable_table_of_content": True,
        "agent": None,
        "learnpack_deploy_url": None,
        "updated_at": UTC_NOW.isoformat().replace("+00:00", "Z"),
        "template_url": None,
        "dependencies": None,
        **data,
    }


def put_serializer(academy, category, asset, data={}):

    return {
        "assessment": asset.assessment,
        "asset_type": asset.asset_type,
        "author": asset.author,
        "enable_table_of_content": asset.enable_table_of_content,
        "interactive": asset.interactive,
        "authors_username": None,
        "category": {"id": category.id, "slug": category.slug, "title": category.title},
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
        "last_synch_at": None,
        "last_test_at": None,
        "last_cleaning_at": None,
        "last_seo_scan_at": None,
        "optimization_rating": None,
        "owner": None,
        "preview": None,
        "published_at": None,
        "readme_url": None,
        "requirements": None,
        "seo_json_status": None,
        "learnpack_deploy_url": None,
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
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("breathecode.registry.signals.asset_slug_modified.send_robust", MagicMock())
    yield


def test__without_auth(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    url = reverse_lazy("registry:academy_asset")
    response = client.get(url)
    json = response.json()

    assert json == {
        "detail": "Authentication credentials were not provided.",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("registry.Asset") == []


def test__without_capability(bc: Breathecode, client: APIClient):
    """Test /certificate without auth"""
    url = reverse_lazy("registry:academy_asset")
    model = bc.database.create(user=1)
    client.force_authenticate(user=model.user)

    response = client.get(url, HTTP_ACADEMY=1)
    json = response.json()
    expected = {"status_code": 403, "detail": "You (user: 1) don't have this capability: read_asset for academy 1"}

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert bc.database.list_of("registry.Asset") == []


def test__post__without_category(bc: Breathecode, client: APIClient):
    """Test /Asset without category"""
    model = bc.database.create(role=1, capability="crud_asset", profile_academy=1, academy=1, user=1)

    client.force_authenticate(user=model.user)
    url = reverse_lazy("registry:academy_asset")
    data = {"slug": "model_slug", "asset_type": "PROJECT", "lang": "es"}
    response = client.post(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()
    expected = {
        "detail": "no-category",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("registry.Asset") == []


@patch("breathecode.registry.tasks.async_pull_from_github.delay", MagicMock())
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test__post__with__all__mandatory__properties(bc: Breathecode, client: APIClient):
    """Test /Asset creation with all mandatory properties"""
    model = bc.database.create(
        role=1,
        capability="crud_asset",
        profile_academy=1,
        academy=1,
        user=1,
        asset_category=1,
    )

    client.force_authenticate(user=model.user)

    url = reverse_lazy("registry:academy_asset")
    data = {"slug": "model_slug", "asset_type": "PROJECT", "lang": "us", "category": 1, "title": "model_slug"}
    response = client.post(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()
    del data["category"]
    expected = post_serializer(model.academy, model.asset_category, data=data)

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert tasks.async_pull_from_github.delay.call_args_list == [call("model_slug")]
    assert bc.database.list_of("registry.Asset") == [database_item(model.academy, model.asset_category, data)]


def test_asset__put_many_without_id(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category=True,
        asset={"category_id": 1, "academy_id": 1, "slug": "asset-1"},
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = {"detail": "without-id", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_asset__put_many_with_wrong_id(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category=True,
        asset={"category_id": 1, "academy_id": 1, "slug": "asset-1"},
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "id": 2,
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = {"detail": "not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_asset__put_many(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset=[
            {
                "test_status": "OK",
                "category_id": 1,
                "lang": "es",
                "academy_id": 1,
                "slug": "asset-1",
                "test_status": "OK",
            },
            {
                "test_status": "OK",
                "category_id": 1,
                "lang": "es",
                "academy_id": 1,
                "slug": "asset-2",
                "test_status": "OK",
            },
        ],
    )
    client.force_authenticate(user=model.user)

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "id": 1,
            "category": 1,
        },
        {
            "id": 2,
            "category": 1,
        },
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    for item in json:
        del item["created_at"]
        del item["updated_at"]

    expected = [
        put_serializer(
            model.academy,
            model.asset_category,
            asset,
            data={
                "test_status": "OK",
            },
        )
        for i, asset in enumerate(model.asset)
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_asset__put_many_with_test_status_ok(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy_id": 1,
            "slug": "asset-1",
            "visibility": "PRIVATE",
            "test_status": "OK",
            "lang": "es",
        },
    )
    client.force_authenticate(user=model.user)

    title = bc.fake.slug()
    date = timezone.now()

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "created_at": bc.datetime.to_iso_string(UTC_NOW),
            "updated_at": bc.datetime.to_iso_string(UTC_NOW),
            "title": title,
            "id": 1,
            "visibility": "PUBLIC",
            "asset_type": "VIDEO",
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = [
        put_serializer(
            model.academy,
            model.asset_category,
            model.asset,
            data={
                "test_status": "OK",
                "created_at": bc.datetime.to_iso_string(UTC_NOW),
                "updated_at": bc.datetime.to_iso_string(UTC_NOW),
                "title": title,
                "id": 1,
                "visibility": "PUBLIC",
                "asset_type": "VIDEO",
            },
        )
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_asset__put_many_with_test_status_warning(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy_id": 1,
            "slug": "asset-1",
            "visibility": "PRIVATE",
            "test_status": "WARNING",
            "lang": "es",
        },
    )
    client.force_authenticate(user=model.user)

    title = bc.fake.slug()
    date = timezone.now()

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "created_at": bc.datetime.to_iso_string(UTC_NOW),
            "updated_at": bc.datetime.to_iso_string(UTC_NOW),
            "title": title,
            "id": 1,
            "visibility": "PUBLIC",
            "asset_type": "VIDEO",
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = [
        put_serializer(
            model.academy,
            model.asset_category,
            model.asset,
            data={
                "test_status": "WARNING",
                "created_at": bc.datetime.to_iso_string(UTC_NOW),
                "updated_at": bc.datetime.to_iso_string(UTC_NOW),
                "title": title,
                "id": 1,
                "visibility": "PUBLIC",
                "asset_type": "VIDEO",
            },
        )
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_asset__put_many_with_test_status_pending(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy_id": 1,
            "slug": "asset-1",
            "visibility": "PRIVATE",
            "test_status": "PENDING",
            "lang": "es",
        },
    )
    client.force_authenticate(user=model.user)

    title = bc.fake.slug()
    date = timezone.now()

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "created_at": bc.datetime.to_iso_string(UTC_NOW),
            "updated_at": bc.datetime.to_iso_string(UTC_NOW),
            "title": title,
            "id": 1,
            "visibility": "PUBLIC",
            "asset_type": "VIDEO",
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = {"detail": "This asset has to pass tests successfully before publishing", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_asset__put_many_with_test_status_error(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy_id": 1,
            "slug": "asset-1",
            "visibility": "PRIVATE",
            "test_status": "ERROR",
            "lang": "es",
        },
    )
    client.force_authenticate(user=model.user)

    title = bc.fake.slug()
    date = timezone.now()

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "created_at": bc.datetime.to_iso_string(UTC_NOW),
            "updated_at": bc.datetime.to_iso_string(UTC_NOW),
            "title": title,
            "id": 1,
            "visibility": "PUBLIC",
            "asset_type": "VIDEO",
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = {"detail": "This asset has to pass tests successfully before publishing", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
def test_asset__put_many_with_test_status_Needs_Resync(bc: Breathecode, client: APIClient):
    """Test Asset bulk update"""

    model = bc.database.create(
        user=1,
        profile_academy=True,
        capability="crud_asset",
        role="potato",
        asset_category={"lang": "es"},
        asset={
            "category_id": 1,
            "academy_id": 1,
            "slug": "asset-1",
            "visibility": "PRIVATE",
            "test_status": "NEEDS_RESYNC",
            "lang": "es",
        },
    )
    client.force_authenticate(user=model.user)

    title = bc.fake.slug()
    date = timezone.now()

    url = reverse_lazy("registry:academy_asset")
    data = [
        {
            "category": 1,
            "created_at": bc.datetime.to_iso_string(UTC_NOW),
            "updated_at": bc.datetime.to_iso_string(UTC_NOW),
            "title": title,
            "id": 1,
            "visibility": "PUBLIC",
            "asset_type": "VIDEO",
        }
    ]

    response = client.put(url, data, format="json", HTTP_ACADEMY=1)
    json = response.json()

    expected = {"detail": "This asset has to pass tests successfully before publishing", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
