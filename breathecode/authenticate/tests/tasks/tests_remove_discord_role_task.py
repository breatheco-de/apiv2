"""
Test cases for remove_discord_role_task
"""

import logging
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.tasks import remove_discord_role_task


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


@pytest.fixture
def mock_discord_service():
    """Mock Discord service with remove_role_to_user method"""
    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_instance = MagicMock()
        mock_discord_class.return_value = mock_instance

        # Mock successful role removal (204 status)
        mock_instance.remove_role_to_user.return_value = 204

        yield mock_instance


def test_remove_discord_role_task_successful_removal_204(mock_discord_service):
    """Test successful role removal with 204 status code"""
    result = remove_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to remove role
    mock_discord_service.remove_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should return 204
    assert result == 204


def test_remove_discord_role_task_removal_failed(mock_discord_service):
    """Test when role removal fails"""
    # Mock failed role removal
    mock_discord_service.remove_role_to_user.return_value = 400

    with pytest.raises(AbortTask) as exc_info:
        remove_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to remove role
    mock_discord_service.remove_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should raise AbortTask with correct message
    assert "Error removing role to user" in str(exc_info.value)

    # Should log error
    assert "Role removal failed: 400" in str(logging.Logger.error.call_args_list[0])


def test_remove_discord_role_task_exception_handling(mock_discord_service):
    """Test exception handling in remove_discord_role_task"""
    # Mock Discord service to raise exception
    mock_discord_service.remove_role_to_user.side_effect = Exception("Discord API error")

    with pytest.raises(AbortTask) as exc_info:
        remove_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to remove role
    mock_discord_service.remove_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should raise AbortTask with correct message
    assert "Error removing role to user: Discord API error" in str(exc_info.value)

    # Should log the exception
    assert "Error removing role to user: Discord API error" in str(logging.Logger.error.call_args_list[0])
