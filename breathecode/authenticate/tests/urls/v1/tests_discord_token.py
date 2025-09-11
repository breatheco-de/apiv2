"""
Test cases for process_discord_token (async Discord OAuth callback)
"""

import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    pass


# Tests for process_discord_token (async Discord OAuth callback endpoint)


# When: User successfully processes Discord token
# Then: Return redirect to original URL
@patch("breathecode.authenticate.views.aiohttp.ClientSession")
def test_process_discord_token_success(mock_session, bc: Breathecode, client: APIClient):
    """Test successful Discord token processing"""
    # Setup
    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-subscription",
            "is_renewable": False,
        }
    )
    model = bc.database.create(user=1, subscription={"plans": [plan.plan.id]}, token=1)

    # Mock Discord API responses
    mock_token_resp = MagicMock()
    mock_token_resp.status = 200
    mock_token_resp.json = AsyncMock(
        return_value={
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 604800,
            "refresh_token": "test_refresh_token",
            "scope": "identify guilds guilds.join",
        }
    )

    mock_user_resp = MagicMock()
    mock_user_resp.status = 200
    mock_user_resp.json = AsyncMock(
        return_value={
            "id": "123456789",
            "username": "testuser",
            "discriminator": "1234",
            "avatar": "test_avatar_hash",
        }
    )

    # Configure the mock session and ensure .post and .get return async context managers
    # Provide a simple async context manager object to be returned by session.post/get
    class DummyRespCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return None

    # Use a plain MagicMock for the session instance; its .post/.get return DummyRespCtx
    mock_session_instance = MagicMock()
    mock_session_instance.post = lambda *a, **k: DummyRespCtx(mock_token_resp)
    mock_session_instance.get = lambda *a, **k: DummyRespCtx(mock_user_resp)

    # Make ClientSession() an async context manager that yields our session instance
    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

    # Test the endpoint
    url = reverse_lazy("authenticate:discord_callback")
    state = f"b'token={model.token.key}|cohort_slug=test-cohort|url=https://google.co.ve'"
    params = {"code": "test_discord_code", "state": state}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    # Debug info
    print(f"Token created: {model.token.key}")
    print(f"Token type: {model.token.token_type}")
    print(f"Token expires: {model.token.expires_at}")

    if response.status_code == 500:
        print("Response content:", response.content.decode())
        print("Response data:", response.data if hasattr(response, "data") else "No data")

    # Should redirect to original URL
    assert response.status_code == status.HTTP_302_FOUND
    assert "https://google.co.ve" in response.url


# When: Discord token exchange fails
# Then: Return bad request
@patch("breathecode.authenticate.views.aiohttp.ClientSession")
def test_process_discord_token_token_exchange_failure(mock_session, bc: Breathecode, client: APIClient):
    """Test Discord token processing when token exchange fails"""
    # Setup
    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-subscription",
            "is_renewable": False,
        }
    )
    model = bc.database.create(user=1, subscription={"plans": [plan.plan.id]}, token=1)

    # Mock failed token response
    mock_token_resp = MagicMock()
    mock_token_resp.status = 400
    mock_token_resp.json = AsyncMock(return_value={"error": "invalid_grant"})

    # Configure mock session
    class DummyRespCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return None

    mock_session_instance = MagicMock()
    mock_session_instance.post = lambda *a, **k: DummyRespCtx(mock_token_resp)

    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

    # Test the endpoint
    url = reverse_lazy("authenticate:discord_callback")
    state = f"b'token={model.token.key}|cohort_slug=test-cohort|url=https://google.co.ve'"
    params = {"code": "invalid_discord_code", "state": state}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    # Should return bad request
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# When: Discord user info retrieval fails
# Then: Return bad request
@patch("breathecode.authenticate.views.aiohttp.ClientSession")
def test_process_discord_token_user_info_failure(mock_session, bc: Breathecode, client: APIClient):
    """Test Discord token processing when user info retrieval fails"""
    # Setup
    plan = bc.database.create(
        plan={
            "slug": "4geeks-plus-subscription",
            "is_renewable": False,
        }
    )
    model = bc.database.create(user=1, subscription={"plans": [plan.plan.id]}, token=1)

    # Mock successful token response but failed user response
    mock_token_resp = MagicMock()
    mock_token_resp.status = 200
    mock_token_resp.json = AsyncMock(
        return_value={
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 604800,
            "refresh_token": "test_refresh_token",
            "scope": "identify guilds guilds.join",
        }
    )

    mock_user_resp = MagicMock()
    mock_user_resp.status = 401
    mock_user_resp.json = AsyncMock(return_value={"message": "401: Unauthorized"})

    # Configure mock session
    class DummyRespCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return None

    mock_session_instance = MagicMock()
    mock_session_instance.post = lambda *a, **k: DummyRespCtx(mock_token_resp)
    mock_session_instance.get = lambda *a, **k: DummyRespCtx(mock_user_resp)

    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

    # Test the endpoint
    url = reverse_lazy("authenticate:discord_callback")
    state = f"b'token={model.token.key}|cohort_slug=test-cohort|url=https://google.co.ve'"
    params = {"code": "test_discord_code", "state": state}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    # Should return bad request
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# When: State parameter is missing
# Then: Return bad request
@patch("breathecode.authenticate.views.aiohttp.ClientSession")
def test_process_discord_token_missing_state(mock_session, bc: Breathecode, client: APIClient):
    """Test Discord token processing when state parameter is missing"""
    # Test the endpoint without state
    url = reverse_lazy("authenticate:discord_callback")
    params = {"code": "test_discord_code"}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    # Should return bad request
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# When: State parameter is invalid
# Then: Return bad request
@patch("breathecode.authenticate.views.aiohttp.ClientSession")
def test_process_discord_token_invalid_state(mock_session, bc: Breathecode, client: APIClient):
    """Test Discord token processing when state parameter is invalid"""
    # Test the endpoint with invalid state
    url = reverse_lazy("authenticate:discord_callback")
    params = {"code": "test_discord_code", "state": "invalid_state"}

    response = client.get(f"{url}?{urllib.parse.urlencode(params)}")

    # Should return bad request
    assert response.status_code == status.HTTP_400_BAD_REQUEST
