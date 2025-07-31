from unittest.mock import AsyncMock, MagicMock, call

import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.registry import views
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

# --- Constants ---
PUT_URL_NAME = "registry:academy_asset_slug_action_slug"  # Name for the PUT endpoint
VALID_PUT_ACTIONS = ["test", "pull", "push", "analyze_seo", "clean", "originality"]  # Actions supported by PUT

# --- Fixtures ---


@pytest.fixture()
def setup_mocks(db, monkeypatch):
    # Mock the update_asset_action static method directly within the view
    mock_update_action = AsyncMock(
        name="mock_update_asset_action", return_value={"serialized": "updated_asset_data"}
    )  # Return mock data
    monkeypatch.setattr(views.AcademyAssetActionView, "update_asset_action", mock_update_action)

    yield {
        "update_asset_action": mock_update_action,
    }


# --- Helpers ---


def get_serializer(utc_now, asset, asset_category):
    return {
        "id": 1,
        "slug": asset.slug,
        "title": asset.title,
        "lang": asset.lang,
        "academy": asset.academy.id if asset.academy else None,
        "config": asset.config,
        "flag_seed": asset.flag_seed,
        "category": (
            {"id": asset_category.id, "slug": asset_category.slug, "title": asset_category.title}
            if asset_category
            else None
        ),
        "asset_type": asset.asset_type,
        "visibility": asset.visibility,
        "url": asset.url,
        "readme_url": asset.readme_url,
        "difficulty": asset.difficulty,
        "duration": asset.duration,
        "description": asset.description,
        "status": asset.status,
        "graded": asset.graded,
        "gitpod": asset.gitpod,
        "enable_table_of_content": asset.enable_table_of_content,
        "interactive": asset.interactive,
        "feature": asset.feature,
        "preview": asset.preview,
        "external": asset.external,
        "solution_video_url": asset.solution_video_url,
        "solution_url": asset.solution_url,
        "intro_video_url": asset.intro_video_url,
        "published_at": asset.published_at,
        "learnpack_deploy_url": asset.learnpack_deploy_url,
        "translations": {},
        "technologies": [],
        "seo_keywords": [],
        "assets_related": [],
        "test_status": asset.test_status,
        "last_test_at": asset.last_test_at,
        "sync_status": asset.sync_status,
        "last_synch_at": asset.last_synch_at,
        "status_text": asset.status_text,
        "readme_updated_at": asset.readme_updated_at,
        "authors_username": asset.authors_username,
        "requirements": asset.requirements,
        "is_seo_tracked": asset.is_seo_tracked,
        "last_seo_scan_at": asset.last_seo_scan_at,
        "seo_json_status": asset.seo_json_status,
        "optimization_rating": asset.optimization_rating,
        "cleaning_status": asset.cleaning_status,
        "cleaning_status_details": asset.cleaning_status_details,
        "last_cleaning_at": asset.last_cleaning_at,
        "assessment": asset.assessment,
        "author": asset.author,
        "owner": asset.owner,
        "created_at": utc_now.isoformat().replace("+00:00", "Z"),
        "updated_at": utc_now.isoformat().replace("+00:00", "Z"),
        "allow_contributions": asset.allow_contributions,
        "clusters": [],
        "previous_versions": [],
    }


# --- Tests ---


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_PUT_ACTIONS)
async def test_put_no_auth(action_slug, aclient: AsyncMock, bc: Breathecode):
    """Test: PUT without authentication"""
    # Arrange
    url = reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": "some-asset", "action_slug": action_slug})
    data = {"some_param": "some_value"}
    # Pass academy_id as a header (even though no auth, decorator might check)
    headers = {"Academy": "1"}

    # Act
    response = await aclient.put(url, data, format="json", headers=headers)

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.parametrize("action_slug", VALID_PUT_ACTIONS)
@pytest.mark.django_db(reset_sequences=True)
async def test_put_no_capability(action_slug, bc: Breathecode, aclient: AsyncMock):
    """Test: PUT without crud_asset capability using Token auth"""
    # Arrange
    role = {"slug": "no_crud_asset_role", "name": "No CRUD"}
    model = await bc.database.acreate(user=1, academy=1, role=role, profile_academy=1, token=1)
    # Use Token authentication instead of force_authenticate
    # aclient.force_authenticate(user=model.user)

    url = str(reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": "some-asset", "action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"some_param": "some_value"}
    headers = {
        "Authorization": f"Token {model.token.key}",
        "Academy": str(model.academy.id),
    }

    # Act
    response = await aclient.put(url, data, format="json", headers=headers)

    # Assert
    # User is authenticated via token and part of academy, but lacks capability -> 403
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.parametrize("action_slug", VALID_PUT_ACTIONS)
@pytest.mark.django_db(reset_sequences=True)
async def test_put_asset_not_found(action_slug, aclient: AsyncMock, bc: Breathecode):
    """Test: PUT when the asset_slug does not exist for the academy"""
    # Arrange
    # Explicitly create capability, role, and profile_academy
    model = await bc.database.acreate(user=1, academy=1, profile_academy=1, token=1, capability="crud_asset", role=1)

    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    non_existent_slug = "non-existent-asset"
    url = str(reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": non_existent_slug, "action_slug": action_slug}))
    # Pass academy_id via header for decorator
    data = {"some_param": "some_value"}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.put(url, data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"This asset {non_existent_slug} does not exist" in content["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action_slug", VALID_PUT_ACTIONS)
@pytest.mark.django_db(reset_sequences=True)
async def test_put_action_success(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: PUT successful execution for a valid asset and action"""
    # Arrange
    # Explicitly create capability, role, and profile_academy
    model = await bc.database.acreate(
        user=1, academy=1, profile_academy=1, asset=1, token=1, capability="crud_asset", role=1
    )

    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": model.asset.slug, "action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    put_data = {"override_meta": True} if action_slug == "pull" else {"custom_field": "value"}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.put(url, put_data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert content == {"serialized": "updated_asset_data"}  # Matches mock return value

    # Verify mock call
    action_mock = setup_mocks["update_asset_action"]

    expected_data = put_data.copy()
    expected_data["action_slug"] = action_slug
    action_mock.assert_called_once_with(model.asset, model.user, expected_data, str(model.academy.id))


@pytest.mark.asyncio
@pytest.mark.parametrize("action_slug", VALID_PUT_ACTIONS)
@pytest.mark.django_db(reset_sequences=True)
async def test_put_action_raises_validation_exception(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: PUT when update_asset_action raises a ValidationException"""
    # Arrange
    # Explicitly create capability, role, and profile_academy
    model = await bc.database.acreate(
        user=1, academy=1, profile_academy=1, asset=1, token=1, capability="crud_asset", role=1
    )

    # Ensure asset is linked to the correct academy
    asset_update = await bc.database.acreate(asset={"academy_id": model.academy.id})
    model.asset = asset_update.asset  # Assign the correctly linked asset

    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": model.asset.slug, "action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"trigger_error": True}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Configure mock to raise ValidationException
    error_message = "Specific action validation failed"
    from capyc.rest_framework.exceptions import ValidationException  # Import locally for safety

    setup_mocks["update_asset_action"].side_effect = ValidationException(error_message, code=400)

    # Act
    response = await aclient.put(url, data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert content["detail"] == error_message
    setup_mocks["update_asset_action"].assert_called_once()


# --- New Test ---
@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize(
    "action_slug",
    [
        "test",
        "clean",
        "pull",
        "push",
        "analyze_seo",
        "originality",
    ],
)
async def test_put_action_success_serialization_check(
    action_slug, aclient: AsyncMock, bc: Breathecode, monkeypatch, utc_now
):
    """
    Test: PUT successful execution, verifying the view reaches the serialization step
    without strictly checking the serialized output structure. It mocks the underlying
    action function called by the real update_asset_action.
    """
    # Arrange
    # --- Mock the underlying action function for this specific test ---
    mock_underlying_action = AsyncMock()

    if action_slug == "test":
        monkeypatch.setattr(views, "atest_asset", mock_underlying_action)
    elif action_slug == "clean":
        monkeypatch.setattr(views, "aclean_asset_readme", mock_underlying_action)
    elif action_slug == "pull":
        monkeypatch.setattr(views, "apull_from_github", mock_underlying_action)
    elif action_slug == "push":
        monkeypatch.setattr(views, "apush_to_github", mock_underlying_action)
    elif action_slug == "analyze_seo":
        # Mock the instance method directly if SEOAnalyzer is instantiated inside the view method
        monkeypatch.setattr(views.SEOAnalyzer, "astart", mock_underlying_action)
    elif action_slug == "originality":
        monkeypatch.setattr(views, "ascan_asset_originality", mock_underlying_action)
    else:
        # Fail test if action_slug is unexpected
        pytest.fail(f"Action slug {action_slug} not handled in test setup")

    # Ensure valid asset type for actions that require it
    asset_kwargs = {"asset_type": "LESSON"}
    if action_slug in ["push", "originality", "analyze_seo"]:
        asset_kwargs["asset_type"] = "LESSON"  # Or ARTICLE as needed

    model = await bc.database.acreate(
        user=1,
        academy=1,
        role=1,
        profile_academy=1,
        asset=asset_kwargs,
        asset_category=1,
        token=1,
        capability="crud_asset",
    )

    url = str(reverse_lazy(PUT_URL_NAME, kwargs={"asset_slug": model.asset.slug, "action_slug": action_slug}))
    put_data = {"action_slug": action_slug}
    if action_slug == "pull":
        put_data["override_meta"] = True
    else:
        # Add some generic data for other actions if needed, or keep it simple
        put_data["custom_field"] = "value"

    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.put(url, put_data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK

    # Basic check that serialization produced a dictionary (non-strict structure check)
    assert content == get_serializer(utc_now, model.asset, model.asset.category)
