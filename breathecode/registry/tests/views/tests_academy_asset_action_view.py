from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from asgiref.sync import sync_to_async
from capyc.rest_framework.exceptions import ValidationException

from breathecode.authenticate.models import User
from breathecode.registry import views as registry_views  # Import views module
from breathecode.registry.models import Asset
from breathecode.registry.views import AcademyAssetActionView
from breathecode.services.seo import SEOAnalyzer  # Corrected Import SEOAnalyzer
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions


# Mock the necessary functions and classes from the actions module and others
@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    # Create mock instances first
    mock_atest_asset = AsyncMock()
    mock_aclean_asset_readme = AsyncMock()
    mock_apull_from_github = AsyncMock()
    mock_apush_to_github = AsyncMock()
    mock_ascan_asset_originality = AsyncMock()
    mock_seo_astart = AsyncMock()
    mock_serializer_instance = MagicMock()
    mock_serializer_instance.data = {"serialized": "data"}  # Ensure .data attribute exists
    mock_serializer_class = MagicMock(return_value=mock_serializer_instance)  # Mock the class constructor
    # mock_api_ext_init = MagicMock(return_value=None)
    # mock_api_ext_lookup = MagicMock()
    # mock_api_ext_paginate = MagicMock()
    # mock_api_ext_sort = MagicMock()
    # mock_api_ext_get = MagicMock()

    # Use monkeypatch.setattr
    monkeypatch.setattr(registry_views, "atest_asset", mock_atest_asset)
    monkeypatch.setattr(registry_views, "aclean_asset_readme", mock_aclean_asset_readme)
    monkeypatch.setattr(registry_views, "apull_from_github", mock_apull_from_github)
    monkeypatch.setattr(registry_views, "apush_to_github", mock_apush_to_github)
    monkeypatch.setattr(registry_views, "ascan_asset_originality", mock_ascan_asset_originality)
    monkeypatch.setattr(SEOAnalyzer, "astart", mock_seo_astart)  # Patch the method on the class (Correct target)

    # Mock sync_to_async to return a factory that produces an awaitable mock
    # which, when awaited, returns the result of the original sync function.
    def mock_sync_to_async_factory(sync_func):
        async_wrapper_mock = AsyncMock(name=f"async_wrapper_for_{sync_func.__name__}")

        # Configure the mock so awaiting it calls the original sync function
        async def side_effect(*args, **kwargs):
            return sync_func(*args, **kwargs)

        async_wrapper_mock.side_effect = side_effect

        return async_wrapper_mock

    monkeypatch.setattr(registry_views, "sync_to_async", mock_sync_to_async_factory)
    monkeypatch.setattr(registry_views, "AcademyAssetSerializer", mock_serializer_class)
    # monkeypatch.setattr(APIViewExtensions, "__init__", mock_api_ext_init)
    # monkeypatch.setattr(APIViewExtensions, "lookup", mock_api_ext_lookup)
    # monkeypatch.setattr(APIViewExtensions, "paginate", mock_api_ext_paginate)
    # monkeypatch.setattr(APIViewExtensions, "sort", mock_api_ext_sort)
    # monkeypatch.setattr(APIViewExtensions, "get", mock_api_ext_get)

    # Return mocks
    return {
        "atest_asset": mock_atest_asset,
        "aclean_asset_readme": mock_aclean_asset_readme,
        "apull_from_github": mock_apull_from_github,
        "apush_to_github": mock_apush_to_github,
        "ascan_asset_originality": mock_ascan_asset_originality,
        "seo_astart": mock_seo_astart,
        "AcademyAssetSerializer": mock_serializer_class,  # Return the class mock
        "serializer_instance": mock_serializer_instance,  # Return the instance mock if needed elsewhere
    }


@pytest.fixture
def view_instance():
    return AcademyAssetActionView


@pytest.fixture
def mock_asset():
    asset = MagicMock(spec=Asset)
    asset.slug = "test-asset"
    asset.asset_type = "LESSON"
    return asset


@pytest.fixture
def mock_user():
    return MagicMock(spec=User)


@pytest.mark.asyncio
async def test_update_asset_action_invalid_slug(view_instance, mock_asset, mock_user):
    with pytest.raises(ValidationException) as exc_info:
        await view_instance.update_asset_action(mock_asset, mock_user, {"action_slug": "invalid-action"})
    assert str(exc_info.value) == "Invalid action invalid-action"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_slug, mock_name, asset_type",  # Use mock_name instead of path
    [
        ("test", "atest_asset", "LESSON"),
        ("clean", "aclean_asset_readme", "LESSON"),
        ("pull", "apull_from_github", "LESSON"),
        ("push", "apush_to_github", "ARTICLE"),
        ("push", "apush_to_github", "LESSON"),
        ("push", "apush_to_github", "QUIZ"),
        ("analyze_seo", "seo_astart", "LESSON"),  # Adjusted mock name
        ("originality", "ascan_asset_originality", "LESSON"),
        ("originality", "ascan_asset_originality", "ARTICLE"),
    ],
)
async def test_update_asset_action_success(
    setup_mocks,
    view_instance,
    mock_asset,
    mock_user,
    action_slug,
    mock_name,
    asset_type,
):
    # Get the specific mock from the setup_mocks fixture return value
    action_mock = setup_mocks[mock_name]
    mock_asset.asset_type = asset_type
    data = {"action_slug": action_slug}
    if action_slug == "pull":
        data["override_meta"] = True  # Test override_meta flag

    # We might need to mock the serializer creation within the view method if it's not patched globally
    # monkeypatch.setattr(registry_views, "AcademyAssetSerializer", MagicMock(return_value=setup_mocks["AcademyAssetSerializer"]))

    result = await view_instance.update_asset_action(mock_asset, mock_user, data)

    assert result == {"serialized": "data"}  # Checks if serializer was called

    if action_slug == "pull":
        action_mock.assert_called_once_with(mock_asset.slug, override_meta=True)
    elif action_slug == "push":
        if asset_type in ["ARTICLE", "LESSON", "QUIZ"]:
            action_mock.assert_called_once_with(mock_asset.slug, owner=mock_user)
        else:
            action_mock.assert_not_called()
    elif action_slug == "analyze_seo":
        # SEOAnalyzer is instantiated, astart is called on the instance.
        # Since we patched SEOAnalyzer.astart directly, we check the mock returned by the fixture.
        action_mock.assert_called_once()
    elif action_slug == "originality":
        if asset_type in ["ARTICLE", "LESSON"]:
            action_mock.assert_called_once_with(mock_asset)
        else:
            action_mock.assert_not_called()
    else:  # test, clean
        action_mock.assert_called_once_with(mock_asset)


@pytest.mark.asyncio
@pytest.mark.parametrize("asset_type", ["PROJECT", "EXERCISE", "VIDEO"])
async def test_update_asset_action_push_invalid_type(view_instance, mock_asset, mock_user, asset_type):
    mock_asset.asset_type = asset_type
    with pytest.raises(ValidationException) as exc_info:
        await view_instance.update_asset_action(mock_asset, mock_user, {"action_slug": "push"})
    assert f"Asset type {asset_type} cannot be pushed to GitHub" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("asset_type", ["PROJECT", "EXERCISE", "VIDEO", "QUIZ"])
async def test_update_asset_action_originality_invalid_type(view_instance, mock_asset, mock_user, asset_type):
    mock_asset.asset_type = asset_type
    with pytest.raises(ValidationException) as exc_info:
        await view_instance.update_asset_action(mock_asset, mock_user, {"action_slug": "originality"})
    assert "Only lessons and articles can be scanned for originality" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_slug, mock_name",  # Use mock_name instead of path
    [
        ("test", "atest_asset"),
        ("clean", "aclean_asset_readme"),
        ("pull", "apull_from_github"),
        ("push", "apush_to_github"),
        ("analyze_seo", "seo_astart"),  # Adjusted mock name
    ],
)
async def test_update_asset_action_exception_in_action(
    setup_mocks, view_instance, mock_asset, mock_user, action_slug, mock_name
):
    error_message = "Something went wrong in the action"
    # Configure the mock from the fixture to raise an exception
    action_mock = setup_mocks[mock_name]
    action_mock.side_effect = Exception(error_message)

    if action_slug == "push":
        mock_asset.asset_type = "LESSON"  # Valid type for push

    with pytest.raises(ValidationException) as exc_info:
        await view_instance.update_asset_action(mock_asset, mock_user, {"action_slug": action_slug})
    assert error_message in str(exc_info.value)


# Tests for create_asset_action


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_slug, mock_name, asset_type",  # Use mock_name instead of path
    [
        ("test", "atest_asset", "LESSON"),
        ("clean", "aclean_asset_readme", "LESSON"),
        ("pull", "apull_from_github", "LESSON"),
        ("push", "apush_to_github", "ARTICLE"),
        ("analyze_seo", "seo_astart", "LESSON"),  # Adjusted mock name
    ],
)
async def test_create_asset_action_success(
    setup_mocks,
    view_instance,
    mock_asset,
    mock_user,
    action_slug,
    mock_name,
    asset_type,
):
    action_mock = setup_mocks[mock_name]
    mock_asset.asset_type = asset_type
    data = {}
    if action_slug == "pull":
        data["override_meta"] = False  # Test override_meta flag

    result = await view_instance.create_asset_action(action_slug, mock_asset, mock_user, data)

    assert result is True

    if action_slug == "pull":
        action_mock.assert_called_once_with(mock_asset.slug, override_meta=False)
    elif action_slug == "push":
        action_mock.assert_called_once_with(mock_asset.slug, owner=mock_user)
    elif action_slug == "analyze_seo":
        action_mock.assert_called_once()
    else:  # test, clean
        action_mock.assert_called_once_with(mock_asset)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_slug, mock_name",  # Use mock_name instead of path
    [
        ("test", "atest_asset"),
        ("clean", "aclean_asset_readme"),
        ("pull", "apull_from_github"),
        ("push", "apush_to_github"),
        ("analyze_seo", "seo_astart"),  # Adjusted mock name
    ],
)
async def test_create_asset_action_failure_exception_in_action(
    setup_mocks, view_instance, mock_asset, mock_user, action_slug, mock_name
):
    error_message = "Action failed"
    action_mock = setup_mocks[mock_name]
    action_mock.side_effect = Exception(error_message)

    if action_slug == "push":
        mock_asset.asset_type = "LESSON"  # Use a valid type to ensure exception is the cause

    result = await view_instance.create_asset_action(action_slug, mock_asset, mock_user, {})

    assert result is False
    action_mock.assert_called_once()  # Check it was still called


@pytest.mark.asyncio
@pytest.mark.parametrize("asset_type", ["PROJECT", "EXERCISE", "VIDEO", "QUIZ"])
async def test_create_asset_action_push_invalid_type_returns_false(view_instance, mock_asset, mock_user, asset_type):
    mock_asset.asset_type = asset_type
    # Note: create_asset_action catches the exception and returns False for invalid push types
    result = await view_instance.create_asset_action("push", mock_asset, mock_user, {})
    assert result is False
