"""
Test cases for assign_discord_role_task
"""

from unittest.mock import MagicMock, patch

import pytest

from breathecode.authenticate.tasks import assign_discord_role_task
from breathecode.tests.mixins.breathecode_mixin import Breathecode


def test_assign_discord_role_task_success(bc: Breathecode, db):
    """Test successful role assignment returns 204"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 204  # Success
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify Discord service was initialized with correct academy
        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        # Verify assign_role_to_user was called with correct parameters
        mock_discord_service.assign_role_to_user.assert_called_once_with(12345, 67890, 11111)

        # Verify task returns success code (successful assignment)
        assert result == 204


def test_assign_discord_role_task_api_failure(bc: Breathecode, db):
    """Test when Discord API returns error code"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 403  # Forbidden
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify Discord service was called
        mock_discord_service.assign_role_to_user.assert_called_once_with(12345, 67890, 11111)

        # Verify task returns the error code
        assert result == 403


def test_assign_discord_role_task_unauthorized(bc: Breathecode, db):
    """Test when Discord API returns 401 Unauthorized - invalid bot token"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("logging.Logger.error") as mock_logger_error,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 401  # Unauthorized
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify error was logged
        mock_logger_error.assert_called_with("Role assignment failed: 401")

        # Verify task returns 401 (bot token invalid)
        assert result == 401


def test_assign_discord_role_task_forbidden_insufficient_permissions(bc: Breathecode, db):
    """Test when Discord API returns 403 Forbidden - bot lacks permissions"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("logging.Logger.error") as mock_logger_error,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 403  # Forbidden
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify error was logged
        mock_logger_error.assert_called_with("Role assignment failed: 403")

        # Verify task returns 403 (insufficient permissions)
        assert result == 403


def test_assign_discord_role_task_not_found_guild_or_user(bc: Breathecode, db):
    """Test when Discord API returns 404 Not Found - guild or user doesn't exist"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("logging.Logger.error") as mock_logger_error,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 404  # Not Found
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=99999, discord_user_id=99999, role_id=11111, academy_id=model.academy.id
        )

        # Verify error was logged
        mock_logger_error.assert_called_with("Role assignment failed: 404")

        # Verify task returns 404 (guild/user/role not found)
        assert result == 404


def test_assign_discord_role_task_exception_raised(bc: Breathecode, db):
    """Test when Discord service raises an exception"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.side_effect = ConnectionError("Discord API unavailable")
        mock_discord_class.return_value = mock_discord_service

        with pytest.raises(Exception) as exc_info:
            assign_discord_role_task(guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id)

        # Verify the exception message includes the original error
        assert "Error assigning role to user: Discord API unavailable" in str(exc_info.value)

        # Verify Discord service was called before failing
        mock_discord_service.assign_role_to_user.assert_called_once_with(12345, 67890, 11111)


@pytest.mark.parametrize("response_code", [400, 401, 403, 404, 429, 500])
def test_assign_discord_role_task_different_error_codes(bc: Breathecode, db, response_code):
    """Test that task handles different Discord API error codes"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = response_code
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify task returns the actual response code
        assert result == response_code

        # Verify Discord service was called
        mock_discord_service.assign_role_to_user.assert_called_once_with(12345, 67890, 11111)


def test_assign_discord_role_task_with_zero_ids(bc: Breathecode, db):
    """Test task behavior with zero/invalid IDs"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 400  # Bad Request
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=0,  # Invalid guild ID
            discord_user_id=0,  # Invalid user ID
            role_id=0,  # Invalid role ID
            academy_id=model.academy.id,
        )

        # Should still call the Discord service (let Discord handle validation)
        mock_discord_service.assign_role_to_user.assert_called_once_with(0, 0, 0)

        # Should return the error code from Discord
        assert result == 400


def test_assign_discord_role_task_already_has_role(bc: Breathecode, db):
    """Test when user already has the role - Discord typically returns 204"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.assign_role_to_user.return_value = 204  # Success (already has role)
        mock_discord_class.return_value = mock_discord_service

        result = assign_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Should treat as success
        assert result == 204
