"""
Test cases for remove_discord_role_task
"""

from unittest.mock import MagicMock, patch

import pytest
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.tasks import remove_discord_role_task
from breathecode.tests.mixins.breathecode_mixin import Breathecode


def test_remove_discord_role_task_success(bc: Breathecode, db):
    """Test successful role removal returns 204"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.remove_role_to_user.return_value = 204  # Success
        mock_discord_class.return_value = mock_discord_service

        result = remove_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Verify Discord service was initialized with correct academy
        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        # Verify remove_role_to_user was called with correct parameters
        mock_discord_service.remove_role_to_user.assert_called_once_with(12345, 67890, 11111)

        # Verify task returns success code (successful removal)
        assert result == 204


def test_remove_discord_role_task_api_error_aborts(bc: Breathecode, db):
    """Test when Discord API returns error code - should abort task"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.remove_role_to_user.return_value = 403  # Forbidden
        mock_discord_class.return_value = mock_discord_service

        with pytest.raises(AbortTask) as exc_info:
            remove_discord_role_task(guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id)

        # Verify AbortTask was raised
        assert "Error removing role to user" in str(exc_info.value)

        # Verify Discord service was called
        mock_discord_service.remove_role_to_user.assert_called_once_with(12345, 67890, 11111)


@pytest.mark.parametrize("error_code", [400, 401, 403, 404, 429, 500])
def test_remove_discord_role_task_different_error_codes_abort(bc: Breathecode, db, error_code):
    """Test that task aborts with different Discord API error codes"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.remove_role_to_user.return_value = error_code
        mock_discord_class.return_value = mock_discord_service

        with pytest.raises(AbortTask) as exc_info:
            remove_discord_role_task(guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id)

        # Verify AbortTask was raised for all error codes
        assert "Error removing role to user" in str(exc_info.value)

        # Verify Discord service was called
        mock_discord_service.remove_role_to_user.assert_called_once_with(12345, 67890, 11111)


def test_remove_discord_role_task_user_doesnt_have_role(bc: Breathecode, db):
    """Test when user doesn't have the role - Discord typically still returns 204"""
    model = bc.database.create(academy=1)

    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_service = MagicMock()
        mock_discord_service.remove_role_to_user.return_value = 204  # Success (user didn't have role)
        mock_discord_class.return_value = mock_discord_service

        result = remove_discord_role_task(
            guild_id=12345, discord_user_id=67890, role_id=11111, academy_id=model.academy.id
        )

        # Should treat as success even if user didn't have the role
        assert result == 204

        # Verify Discord service was called
        mock_discord_service.remove_role_to_user.assert_called_once_with(12345, 67890, 11111)
