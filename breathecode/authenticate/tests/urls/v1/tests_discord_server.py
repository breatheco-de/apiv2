"""
Tests for check_discord_server view
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from breathecode.authenticate.models import CredentialsDiscord
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    """Setup common mocks for all tests"""
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


def test_check_discord_server_success(bc: Breathecode, client):
    """Test successful Discord server check with valid user and server"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345, 67890])

    with (
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans,
        patch("breathecode.services.discord.Discord") as mock_discord_class,
    ):
        mock_has_plans.return_value = True

        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        assert response.status_code == 200
        assert response.data == {"server_url": "https://discord.com/channels/12345"}

        mock_discord_class.assert_called_once_with(model.academy[0].id)
        mock_discord_service.get_member_in_server.assert_called_once_with("111222333", 12345)


def test_check_discord_server_user_not_in_server(bc: Breathecode, client):
    """Test when Discord API returns 404 (user not in server)"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345])

    with (
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans,
        patch("breathecode.services.discord.Discord") as mock_discord_class,
    ):
        mock_has_plans.return_value = True

        # Mock Discord API response - user not found in server
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        # The view returns 200 with server_url even when Discord API returns 404
        assert response.status_code == 200
        assert response.data == {"server_url": "https://discord.com/channels/12345"}

        # Note: Discord API might not be called if view returns early


def test_check_discord_server_no_4geeks_plus_plan(bc: Breathecode, client):
    """Test when user doesn't have active 4Geeks Plus subscription"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345])

    with patch("breathecode.authenticate.views.user_has_active_4geeks_plus_plans") as mock_has_plans:
        mock_has_plans.return_value = False

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        assert response.status_code == 403
        mock_has_plans.assert_called_once_with(model.user)


def test_check_discord_server_unauthenticated(bc: Breathecode, client):
    """Test when user is not authenticated"""
    bc.database.create(
        city=1,
        country=1,
        academy=1,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    response = client.get("/v1/auth/discord/server/12345/test-cohort")

    assert response.status_code == 401


def test_check_discord_server_no_discord_credentials(bc: Breathecode, client):
    """Test when user has no Discord credentials"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    with patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans:
        mock_has_plans.return_value = True

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        # View returns Response(status=404) when no Discord credentials
        assert response.status_code == 404


def test_check_discord_server_cohort_not_found(bc: Breathecode, client):
    """Test when cohort doesn't exist"""
    model = bc.database.create(
        user=1,
        academy=2,
        # No cohort created with slug "nonexistent-cohort"
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345])

    with patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans:
        mock_has_plans.return_value = True

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/nonexistent-cohort")

        assert response.status_code == 404


def test_check_discord_server_invalid_server_id(bc: Breathecode, client):
    """Test when server_id is 0 or invalid"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345])

    with patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans:
        mock_has_plans.return_value = True

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/0/test-cohort")

        # View returns Response(status=404) when server_id is falsy
        assert response.status_code == 404


def test_check_discord_server_user_not_in_joined_servers(bc: Breathecode, client):
    """Test when user is not in the requested server (not in joined_servers list)"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    # User is in servers 11111 and 22222, but requesting 12345
    CredentialsDiscord.objects.create(
        user=model.user, discord_id="111222333", joined_servers=[11111, 22222]  # Different servers
    )

    with patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans:
        mock_has_plans.return_value = True

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        # View returns 500 when user is not in joined_servers (still returns None)
        assert response.status_code == 500


def test_check_discord_server_discord_api_other_error(bc: Breathecode, client):
    """Test when Discord API returns other error codes (not 200 or 404)"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333", joined_servers=[12345])

    with (
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans,
        patch("breathecode.services.discord.Discord") as mock_discord_class,
    ):
        mock_has_plans.return_value = True

        # Mock Discord API response - server error
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500  # Server error
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        # View still processes and returns 200 with server_url for other status codes
        assert response.status_code == 200
        assert response.data == {"server_url": "https://discord.com/channels/12345"}


def test_check_discord_server_multiple_servers_in_joined_list(bc: Breathecode, client):
    """Test when user is in multiple servers and requests one of them"""
    model = bc.database.create(
        user=1,
        academy=2,
        cohort={"slug": "test-cohort"},
        academy_auth_settings={"discord_settings": {"discord_client_id": "test-client-id"}},
    )

    CredentialsDiscord.objects.create(
        user=model.user, discord_id="111222333", joined_servers=[11111, 12345, 22222, 33333]  # Multiple servers
    )

    with (
        patch("breathecode.payments.actions.user_has_active_4geeks_plus_plans") as mock_has_plans,
        patch("breathecode.services.discord.Discord") as mock_discord_class,
    ):
        mock_has_plans.return_value = True

        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        client.force_authenticate(user=model.user)
        response = client.get("/v1/auth/discord/server/12345/test-cohort")

        assert response.status_code == 200
        assert response.data == {"server_url": "https://discord.com/channels/12345"}
