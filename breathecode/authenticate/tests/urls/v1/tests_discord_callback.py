"""
Test /v1/auth/discord/callback
"""

import json
from unittest.mock import MagicMock, call

import aiohttp
import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


class StreamReaderMock:
    def __init__(self, data):
        self.data = data

    async def read(self):
        return self.data


class ResponseMock:
    def __init__(self, data, status=200, headers={}):
        self.content = data
        self.status = status
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return json.loads(self.content.data.decode())


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):
    monkeypatch.setenv("DISCORD_REDIRECT_URL", "https://breathecode.herokuapp.com/v1/auth/discord/callback")
    monkeypatch.setattr("breathecode.authenticate.tasks.join_user_to_discord_guild.delay", MagicMock())

    yield


@pytest.fixture
def patch_discord_calls(monkeypatch):
    def handler(oauth_response, user_response, oauth_status=200, user_status=200):
        # Track call order
        call_order = []

        # Mock for OAuth token call
        oauth_reader = StreamReaderMock(json.dumps(oauth_response).encode())
        oauth_mock = ResponseMock(oauth_reader, oauth_status)

        # Mock for user info call
        user_reader = StreamReaderMock(json.dumps(user_response).encode())
        user_mock = ResponseMock(user_reader, user_status)

        class MockSession:
            def __init__(self):
                self.call_order = call_order

            def post(self, *args, **kwargs):
                self.call_order.append(("post", args, kwargs))
                return oauth_mock

            def get(self, *args, **kwargs):
                self.call_order.append(("get", args, kwargs))
                return user_mock

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        # Mock the ClientSession class to return our MockSession instance
        def mock_client_session(*args, **kwargs):
            return MockSession()

        monkeypatch.setattr("aiohttp.ClientSession", mock_client_session)

        return call_order

    yield handler


def test_successful_discord_oauth(bc: Breathecode, client: APIClient, patch_discord_calls):
    # Create test data
    model = bc.database.create(
        token={"token_type": "temporal"},
        cohort={"slug": "test-cohort"},
        academy=1,
        city=1,
        country=1,
        academy_auth_settings={"discord_settings": {"discord_client_id": "123456789", "discord_secret": "secret123"}},
    )

    # Build URL with state parameter
    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    # Mock responses
    oauth_response = {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "test_refresh_token",
        "scope": "identify email",
    }

    user_response = {
        "id": "123456789012345678",
        "username": "testuser",
        "discriminator": "0001",
        "email": "test@example.com",
        "verified": True,
    }

    # Setup mocks
    call_order = patch_discord_calls(oauth_response, user_response)

    # Make the request
    response = client.get(url, format="json")

    # Debug: Print response details
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content}")
    if hasattr(response, "json"):
        try:
            print(f"Response JSON: {response.json()}")
        except:
            pass

    # Assertions
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == "https://4geeks.com"

    # Verify call order (OAuth first, then user info)
    assert len(call_order) == 2
    assert call_order[0][0] == "post"  # First call should be POST (OAuth)
    assert call_order[1][0] == "get"  # Second call should be GET (user info)


def test_missing_state_parameter(bc: Breathecode, client: APIClient):
    """Test when state parameter is missing from URL"""
    url = reverse_lazy("authenticate:discord_callback") + "?code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_missing_token_in_state(bc: Breathecode, client: APIClient):
    """Test when token is missing from state parameter"""
    state = f"b'url=https://4geeks.com|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_token_not_found(bc: Breathecode, client: APIClient):
    """Test when token from state doesn't exist in database"""
    state = f"b'url=https://4geeks.com|token=non_existent_token|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_cohort_not_found(bc: Breathecode, client: APIClient):
    """Test when cohort from state doesn't exist in database"""
    model = bc.database.create(
        token={"token_type": "temporal"},
        academy=1,
        academy_auth_settings={"discord_settings": {"discord_client_id": "123456789", "discord_secret": "secret123"}},
    )

    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=non_existent_cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_missing_discord_settings(bc: Breathecode, client: APIClient):
    """Test when academy doesn't have discord settings configured"""
    model = bc.database.create(
        token={"token_type": "temporal"},
        cohort={"slug": "test-cohort", "city": 1, "country": 1},
        academy=1,
        academy_auth_settings={},  # No discord settings
    )

    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_discord_oauth_error(bc: Breathecode, client: APIClient, patch_discord_calls):
    """Test when Discord OAuth returns an error"""
    model = bc.database.create(
        token={"token_type": "temporal"},
        cohort={"slug": "test-cohort", "city": 1, "country": 1},
        academy=1,
        academy_auth_settings={"discord_settings": {"discord_client_id": "123456789", "discord_secret": "secret123"}},
    )

    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    # Discord OAuth returns error
    oauth_response = {"error": "invalid_grant", "error_description": "The authorization code is invalid or has expired"}

    user_response = {}  # Won't be reached

    call_order = patch_discord_calls(oauth_response, user_response, oauth_status=400)

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert len(call_order) == 1  # Only OAuth call, user call not reached
    assert call_order[0][0] == "post"


def test_discord_user_api_error(bc: Breathecode, client: APIClient, patch_discord_calls):
    """Test when Discord user API returns an error"""
    model = bc.database.create(
        token={"token_type": "temporal"},
        cohort={"slug": "test-cohort", "city": 1, "country": 1},
        academy=1,
        academy_auth_settings={"discord_settings": {"discord_client_id": "123456789", "discord_secret": "secret123"}},
    )

    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}&code=12345"

    oauth_response = {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "test_refresh_token",
        "scope": "identify email",
    }

    # Discord user API returns error
    user_response = {"message": "401: Unauthorized", "code": 0}

    call_order = patch_discord_calls(oauth_response, user_response, user_status=401)

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert len(call_order) == 2  # Both calls made
    assert call_order[0][0] == "post"
    assert call_order[1][0] == "get"


def test_missing_code_parameter(bc: Breathecode, client: APIClient):
    """Test when code parameter is missing from URL"""
    model = bc.database.create(
        token={"token_type": "temporal"},
        cohort={"slug": "test-cohort", "city": 1, "country": 1},
        academy=1,
        academy_auth_settings={"discord_settings": {"discord_client_id": "123456789", "discord_secret": "secret123"}},
    )

    state = f"b'url=https://4geeks.com|token={model.token.key}|cohort_slug=test-cohort'"
    url = reverse_lazy("authenticate:discord_callback") + f"?state={state}"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_302_FOUND


def test_empty_state_parameter(bc: Breathecode, client: APIClient):
    """Test when state parameter is empty"""
    url = reverse_lazy("authenticate:discord_callback") + "?state=&code=12345"

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
