# --- Constants ---
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.registry import views
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

POST_URL_NAME = "registry:academy_asset_action_slug"  # Correct name for the POST endpoint
VALID_POST_ACTIONS = ["test", "pull", "push", "analyze_seo"]  # Actions supported by POST

# --- Fixtures ---


# Mocks for action functions and serializer
@pytest.fixture(autouse=True)
def setup_mocks(db, monkeypatch):
    # Mock the create_asset_action static method directly within the view
    mock_create_action = AsyncMock(name="mock_create_asset_action", return_value=True)  # Assume success by default
    monkeypatch.setattr(views.AcademyAssetActionView, "create_asset_action", mock_create_action)

    # Mock the serializer to prevent database lookups within it during response generation
    # (this might not be strictly necessary if create_asset_action handles all logic,
    # but it isolates the test further)
    mock_serializer_instance = MagicMock()
    mock_serializer_instance.data = {"some_success": "message"}  # Placeholder success data
    monkeypatch.setattr(
        "breathecode.registry.views.AcademyAssetSerializer", MagicMock(return_value=mock_serializer_instance)
    )

    # Mock sync_to_async as it might be used internally
    def mock_sync_to_async_factory(sync_func):
        async_wrapper_mock = AsyncMock(name=f"async_wrapper_for_{getattr(sync_func, '__name__', 'lambda')}")

        async def side_effect(*args, **kwargs):
            # Determine the actual return value based on mocked behavior if needed
            # For now, just return a placeholder or the result of the mocked function
            return sync_func(*args, **kwargs)

        async_wrapper_mock.side_effect = side_effect
        return async_wrapper_mock

    monkeypatch.setattr(views, "sync_to_async", mock_sync_to_async_factory)

    # Yield the crucial mock for assertion checks
    yield {
        "create_asset_action": mock_create_action,
        "serializer": views.AcademyAssetSerializer,
    }


# --- Helper Function to generate expected response messages ---
def expected_response_message(action_slug, successful_slugs, failed_slugs, academy_id=None):
    success_msg = ""
    fail_msg = ""

    if successful_slugs:
        # Use a generic success message as the exact wording might vary
        success_msg = f"Successfully processed action '{action_slug}' for: {successful_slugs!r}. "
    if failed_slugs:
        # Use a generic failure message
        fail_msg = f"Failed to process action '{action_slug}' for: {failed_slugs!r}. "

    # Specific handling for non-existent assets
    if any("non-existent-slug" in f for f in failed_slugs):
        fail_msg = (
            f"These assets {[s for s in failed_slugs if s == 'non-existent-slug']!r} do not exist for this academy {academy_id}. "
            + fail_msg.replace(
                f"Failed to process action '{action_slug}' for: {[s for s in failed_slugs if s == 'non-existent-slug']!r}. ",
                "",
            )
        )

    return success_msg + fail_msg.strip()


# --- Tests ---


@pytest.mark.asyncio
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_no_auth(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST without authentication"""
    # Arrange
    # Note: No academy_id needed based on NoReverseMatch errors
    url = reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug})
    data = {"assets": ["some-asset"]}

    # Act
    response = await aclient.post(url, data, format="json")

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_no_capability(action_slug, bc: Breathecode, aclient: AsyncMock, setup_mocks):
    """Test: POST without crud_asset capability using Token auth"""
    # Arrange
    role = {"slug": "no_crud_asset_role", "name": "No CRUD"}
    model = await bc.database.acreate(user=1, academy=1, role=role, profile_academy=1, token=1)
    # Use Token authentication instead of force_authenticate
    # aclient.force_authenticate(user=model.user)

    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"assets": ["some-asset"]}
    headers = {
        "Authorization": f"Token {model.token.key}",
        "Academy": str(model.academy.id),
    }

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)

    # Assert
    # User is authenticated via token and part of academy, but lacks capability -> 403
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_post_invalid_action_slug(aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST with an invalid action slug"""
    # Arrange
    model = await bc.database.acreate(user=1, academy=1, capability="crud_asset", role=1, token=1, profile_academy=1)
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    invalid_action = "invalid-action"
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": invalid_action}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"assets": ["some-asset"]}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert content["detail"] == f"Invalid action {invalid_action}"


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_missing_assets_in_body(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST without 'assets' key in the request body"""
    # Arrange
    model = await bc.database.acreate(user=1, academy=1, capability="crud_asset", role=1, token=1, profile_academy=1)
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {}  # Missing 'assets'
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert content["detail"] == "Assets not found in the body of the request."


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_empty_assets_list(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST with an empty 'assets' list in the request body"""
    # Arrange
    model = await bc.database.acreate(user=1, academy=1, capability="crud_asset", role=1, token=1, profile_academy=1)
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"assets": []}  # Empty list
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert content["detail"] == "The list of Assets is empty."


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_asset_not_found_in_db(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST with asset slugs where one doesn't exist in the DB"""
    # Arrange
    asset1 = await bc.database.acreate(asset=1, academy=1)
    model = await bc.database.acreate(
        user=1, academy=asset1.academy, capability="crud_asset", role=1, token=1, profile_academy=1
    )
    # Use Token auth
    # aclient.force_authenticate(user=model.user)

    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    non_existent_slug = "non-existent-slug"
    data = {"assets": [asset1.asset.slug, non_existent_slug]}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.content.decode("utf-8")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # The response content is now a plain string, not JSON with 'detail'
    assert non_existent_slug in content
    assert asset1.asset.slug in content
    assert "do not exist" in content

    # Check create_asset_action was called for the valid asset only
    setup_mocks["create_asset_action"].assert_called_once_with(action_slug, asset1.asset, model.user, data)


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_action_success_single_asset(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST successful execution for a single asset"""
    # Arrange
    model = await bc.database.acreate(
        user=1, academy=1, asset=1, asset_category=1, capability="crud_asset", role=1, token=1, profile_academy=1
    )
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"assets": [model.asset.slug]}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.content.decode("utf-8")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # The response content is now a plain string, not JSON with 'detail'
    assert model.asset.slug in content
    assert "failed" not in content

    # Verify mock call
    action_mock = setup_mocks["create_asset_action"]
    action_mock.assert_called_once_with(action_slug, model.asset, model.user, data)


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_action_success_multiple_assets(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST successful execution for multiple assets"""
    # Arrange
    model = await bc.database.acreate(
        user=1, academy=1, asset=2, asset_category=1, capability="crud_asset", role=1, token=1, profile_academy=1
    )
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    asset_slugs = [a.slug for a in model.asset]
    data = {"assets": asset_slugs}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.content.decode("utf-8")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # The response content is now a plain string
    assert all(slug in content for slug in asset_slugs)
    assert "failed" not in content

    # Verify mock call for each asset
    action_mock = setup_mocks["create_asset_action"]
    assert action_mock.call_count == 2
    # Create expected calls using the actual asset instances
    expected_calls = [
        call(action_slug, model.asset[0], model.user, data),
        call(action_slug, model.asset[1], model.user, data),
    ]
    action_mock.assert_has_calls(expected_calls, any_order=True)


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("action_slug", VALID_POST_ACTIONS)
async def test_post_action_fails_for_one_asset(action_slug, aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test: POST when action fails for one asset out of two"""
    # Arrange
    model = await bc.database.acreate(
        user=1, academy=1, asset=2, asset_category=1, capability="crud_asset", role=1, token=1, profile_academy=1
    )
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    asset_slugs = [a.slug for a in model.asset]
    successful_asset = model.asset[0]
    failing_asset = model.asset[1]
    data = {"assets": asset_slugs}
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Configure mock to fail (return False) for the second asset
    async def side_effect_checker(slug, asset, user, req_data):
        if asset.id == failing_asset.id:
            return False  # Simulate failure
        return True  # Simulate success

    setup_mocks["create_asset_action"].side_effect = side_effect_checker

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.content.decode("utf-8")

    # Assert
    assert response.status_code == status.HTTP_200_OK  # Endpoint still returns 200

    # Check response message indicates partial failure (plain string check)
    assert successful_asset.slug in content
    assert failing_asset.slug in content
    assert f"These asset readmes were pulled correctly from GitHub: ['{successful_asset.slug}']." in content
    assert f"These assets ['{failing_asset.slug}'] do not exist for this academy {model.academy.id}" in content

    # Verify mock was called for both
    action_mock = setup_mocks["create_asset_action"]
    assert action_mock.call_count == 2


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_post_pull_with_override_meta(aclient: AsyncMock, bc: Breathecode, setup_mocks):
    """Test POST 'pull' action specifically with override_meta=True in request body"""
    # Arrange
    model = await bc.database.acreate(
        user=1, academy=1, asset=1, asset_category=1, capability="crud_asset", role=1, token=1, profile_academy=1
    )
    # Use Token auth
    # aclient.force_authenticate(user=model.user)
    action_slug = "pull"
    url = str(reverse_lazy(POST_URL_NAME, kwargs={"action_slug": action_slug}))
    # Pass academy_id via header for decorator
    # url_with_query = f"{url}?academy={model.academy.id}"
    data = {"assets": [model.asset.slug], "override_meta": True}  # Request body includes override
    headers = {"Authorization": f"Token {model.token.key}", "Academy": str(model.academy.id)}

    # Act
    response = await aclient.post(url, data, format="json", headers=headers)
    content = response.content.decode("utf-8")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # The response content is now a plain string
    assert model.asset.slug in content
    assert "failed" not in content

    # Verify mock call with override_meta=True passed in data dict
    action_mock = setup_mocks["create_asset_action"]
    action_mock.assert_called_once_with(
        action_slug,
        model.asset,
        model.user,
        data,  # data includes override
    )
