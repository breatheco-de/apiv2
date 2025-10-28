"""
Test cases for revoke_user_discord_permissions action
"""

from unittest.mock import MagicMock, patch

import pytest

from breathecode.authenticate.actions import revoke_user_discord_permissions
from breathecode.authenticate.models import CredentialsDiscord
from breathecode.tests.mixins.breathecode_mixin import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    """Setup common mocks for all tests"""
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    yield


def test_revoke_user_discord_permissions_user_had_roles(bc: Breathecode, db):
    """Test successful revocation when user had Discord roles"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "67890"}]},
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        # Mock Discord API response - user has the role
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["67890", "other_role"]}  # User has the role
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        mock_discord_service.get_member_in_server.assert_called_once_with(111222333, "12345")

        mock_remove_task.assert_called_once_with("12345", 111222333, "67890", academy_id=model.academy.id)

        # Verify DM task was scheduled (user had roles)
        mock_dm_task.assert_called_once_with(
            111222333,
            "Your 4Geeks Plus subscription has ended, your roles have been removed. Renew your subscription to get them back: https://4geeks.com/checkout?plan=4geeks-plus-subscription",
            model.academy.id,
        )

        # Verify function returns True (user had roles)
        assert result is True


def test_revoke_user_discord_permissions_user_had_no_roles(bc: Breathecode, db):
    """Test when user had no Discord roles"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "67890"}]},
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        # Mock Discord API response - user doesn't have the role
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["other_role"]}  # User doesn't have target role
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        mock_discord_service.get_member_in_server.assert_called_once_with(111222333, "12345")

        # Verify remove_discord_role_task was NOT scheduled (user doesn't have the target role)
        assert not mock_remove_task.called

        assert not mock_dm_task.called

        assert result is False


def test_revoke_user_discord_permissions_no_discord_credentials(bc: Breathecode, db):
    """Test when user has no Discord credentials"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort=1,
        cohort_user=1,
        # No Discord credentials created
    )

    with (
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        result = revoke_user_discord_permissions(model.user, model.academy)

        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no credentials)
        assert result is False


def test_revoke_user_discord_permissions_no_discord_shortcuts(bc: Breathecode, db):
    """Test when cohorts have no Discord shortcuts"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": None},  # No shortcuts
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify no tasks were scheduled (no Discord shortcuts)
        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no roles to revoke)
        assert result is False


def test_revoke_user_discord_permissions_non_discord_shortcuts(bc: Breathecode, db):
    """Test when cohorts have shortcuts but none are Discord"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={
            "shortcuts": [
                {"label": "Slack", "server_id": "12345"},
                {"label": "GitHub", "server_id": "67890"},
            ]
        },
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify no tasks were scheduled (no Discord shortcuts)
        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no Discord roles to revoke)
        assert result is False


def test_revoke_user_discord_permissions_discord_api_error(bc: Breathecode, db):
    """Test when Discord API returns error when checking member"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "67890"}]},
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
        patch("logging.Logger.warning") as mock_logger_warning,
    ):
        # Mock Discord API response - API error
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404  # User not found in server
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        mock_discord_service.get_member_in_server.assert_called_once_with(111222333, "12345")

        # Verify warning was logged for API error
        mock_logger_warning.assert_called_once_with("Could not get user 111222333 info from server 12345: 404")

        # Verify remove_discord_role_task was scheduled (when API fails, schedule all as safety measure)
        mock_remove_task.assert_called_once_with("12345", 111222333, "67890", academy_id=model.academy.id)

        # Verify DM task was NOT scheduled (user_had_roles is False when API fails)
        assert not mock_dm_task.called

        # Verify function returns False (no roles verified due to API error)
        assert result is False


def test_revoke_user_discord_permissions_discord_service_exception(bc: Breathecode, db):
    """Test when Discord service raises exception"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "67890"}]},
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
        patch("logging.Logger.error") as mock_logger_error,
    ):
        # Mock Discord service to raise exception
        mock_discord_service = MagicMock()
        mock_discord_service.get_member_in_server.side_effect = ConnectionError("API unavailable")
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify exception was logged with new message format
        mock_logger_error.assert_called_with("Error checking/removing Discord roles for server 12345: API unavailable")

        # Verify no tasks were scheduled due to exception
        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no roles processed due to exception)
        assert result is False


def test_revoke_user_discord_permissions_multiple_cohorts_with_roles(bc: Breathecode, db):
    """Test when user has roles in multiple cohorts"""
    model = bc.database.create(
        user=1,
        academy=1,
    )

    # Create multiple cohorts with Discord shortcuts
    cohort1 = bc.database.create(
        cohort={"academy": model.academy, "shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "67890"}]}
    )

    cohort2 = bc.database.create(
        cohort={"academy": model.academy, "shortcuts": [{"label": "Discord", "server_id": "54321", "role_id": "09876"}]}
    )

    # Add user to both cohorts
    bc.database.create(cohort_user={"cohort": cohort1.cohort, "user": model.user})
    bc.database.create(cohort_user={"cohort": cohort2.cohort, "user": model.user})

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    def mock_get_member_response(discord_user_id, server_id):
        """Mock different responses based on server_id"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        if server_id == "12345":
            mock_response.json.return_value = {"roles": ["67890", "other_role"]}
        elif server_id == "54321":
            mock_response.json.return_value = {"roles": ["09876", "another_role"]}
        return mock_response

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        # Mock Discord API responses - different roles per server
        mock_discord_service = MagicMock()
        mock_discord_service.get_member_in_server.side_effect = mock_get_member_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify Discord service was called for both servers
        assert mock_discord_service.get_member_in_server.call_count == 2

        # Verify remove_discord_role_task was called for both roles
        assert mock_remove_task.call_count == 2

        # Verify DM task was scheduled (user had roles)
        mock_dm_task.assert_called_once_with(
            111222333,
            "Your 4Geeks Plus subscription has ended, your roles have been removed. Renew your subscription to get them back: https://4geeks.com/checkout?plan=4geeks-plus-subscription",
            model.academy.id,
        )

        assert result is True


def test_revoke_user_discord_permissions_no_cohorts(bc: Breathecode, db):
    """Test when user has no cohorts in the academy"""
    model = bc.database.create(
        user=1,
        academy=1,
        # No cohorts or cohort_user created
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify no tasks were scheduled (no cohorts)
        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no roles to revoke)
        assert result is False


def test_revoke_user_discord_permissions_discord_shortcut_missing_server_id(bc: Breathecode, db):
    """Test when Discord shortcut is missing server_id"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": None, "role_id": "67890"}]},  # Missing server_id
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify no tasks were scheduled (missing server_id)
        assert not mock_remove_task.called
        assert not mock_dm_task.called

        # Verify function returns False (no valid Discord shortcuts)
        assert result is False


def test_revoke_user_discord_permissions_same_server_multiple_roles(bc: Breathecode, db):
    """Test optimization: multiple roles in same server are grouped together"""
    model = bc.database.create(
        user=1,
        academy=1,
    )

    # Create multiple cohorts with same server but different roles
    cohort1 = bc.database.create(
        cohort={
            "academy": model.academy,
            "shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "role1"}],  # Same server
        }
    )

    cohort2 = bc.database.create(
        cohort={
            "academy": model.academy,
            "shortcuts": [{"label": "Discord", "server_id": "12345", "role_id": "role2"}],  # Same server
        }
    )

    # Add user to both cohorts
    bc.database.create(cohort_user={"cohort": cohort1.cohort, "user": model.user})
    bc.database.create(cohort_user={"cohort": cohort2.cohort, "user": model.user})

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        # Mock Discord API response - user has both roles
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["role1", "role2", "other_role"]}
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify Discord service was created only once
        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        # Verify get_member_in_server was called only ONCE for the server (optimization!)
        mock_discord_service.get_member_in_server.assert_called_once_with(111222333, "12345")

        # Verify remove_discord_role_task was called for BOTH roles
        assert mock_remove_task.call_count == 2

        # Verify both roles were scheduled for removal
        calls = mock_remove_task.call_args_list
        role_ids_called = [call[0][2] for call in calls]  # Third argument is role_id
        assert "role1" in role_ids_called
        assert "role2" in role_ids_called

        mock_dm_task.assert_called_once_with(
            111222333,
            "Your 4Geeks Plus subscription has ended, your roles have been removed. Renew your subscription to get them back: https://4geeks.com/checkout?plan=4geeks-plus-subscription",
            model.academy.id,
        )

        assert result is True


def test_revoke_user_discord_permissions_partial_roles_optimization(bc: Breathecode, db):
    """Test optimization: only schedule tasks for roles the user actually has"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={
            "shortcuts": [
                {"label": "Discord", "server_id": "12345", "role_id": "role1"},
                {"label": "Discord", "server_id": "12345", "role_id": "role2"},
                {"label": "Discord", "server_id": "12345", "role_id": "role3"},
            ]
        },
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
        patch("breathecode.authenticate.tasks.send_discord_dm_task.delay") as mock_dm_task,
    ):
        # Mock Discord API response - user only has role1 and role3 (not role2)
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["role1", "role3", "other_role"]}  # Missing role2
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        result = revoke_user_discord_permissions(model.user, model.academy)

        # Verify get_member_in_server was called once
        mock_discord_service.get_member_in_server.assert_called_once_with(111222333, "12345")

        # Verify remove_discord_role_task was called only for roles the user HAS (role1, role3)
        assert mock_remove_task.call_count == 2  # Only 2 out of 3 roles

        # Verify only role1 and role3 were scheduled (not role2)
        calls = mock_remove_task.call_args_list
        role_ids_called = [call[0][2] for call in calls]  # Third argument is role_id
        assert "role1" in role_ids_called
        assert "role3" in role_ids_called
        assert "role2" not in role_ids_called  # This is the optimization!

        # Verify DM task was scheduled (user had some roles)
        mock_dm_task.assert_called_once_with(
            111222333,
            "Your 4Geeks Plus subscription has ended, your roles have been removed. Renew your subscription to get them back: https://4geeks.com/checkout?plan=4geeks-plus-subscription",
            model.academy.id,
        )

        # Verify function returns True (user had some roles)
        assert result is True


def test_revoke_user_discord_permissions_single_discord_service_instance(bc: Breathecode, db):
    """Test optimization: single Discord service instance is reused"""
    model = bc.database.create(
        user=1,
        academy=1,
        cohort={
            "shortcuts": [
                {"label": "Discord", "server_id": "server1", "role_id": "role1"},
                {"label": "Discord", "server_id": "server2", "role_id": "role2"},
            ]
        },
        cohort_user=1,
    )

    CredentialsDiscord.objects.create(user=model.user, discord_id="111222333")

    with (
        patch("breathecode.services.discord.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.remove_discord_role_task.delay") as mock_remove_task,
    ):
        # Mock Discord API responses
        mock_discord_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["role1", "role2"]}
        mock_discord_service.get_member_in_server.return_value = mock_response
        mock_discord_class.return_value = mock_discord_service

        revoke_user_discord_permissions(model.user, model.academy)

        # Verify Discord service was created only ONCE (optimization!)
        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        # Verify get_member_in_server was called twice (once per server)
        assert mock_discord_service.get_member_in_server.call_count == 2
