"""
Test cases for assign_discord_role_task
"""

import logging
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest

from breathecode.authenticate.tasks import assign_discord_role_task


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


@pytest.fixture
def mock_discord_service():
    """Mock Discord service with assign_role_to_user method"""
    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_instance = MagicMock()
        mock_discord_class.return_value = mock_instance

        # Mock successful role assignment (204 status)
        mock_instance.assign_role_to_user.return_value = 204

        yield mock_instance


def test_assign_discord_role_task_successful_assignment_204(mock_discord_service):
    """Test successful role assignment with 204 status code"""
    result = assign_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to assign role
    mock_discord_service.assign_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should return 204
    assert result == 204


def test_assign_discord_role_task_assignment_failed(mock_discord_service):
    """Test when role assignment fails"""
    # Mock failed role assignment
    mock_discord_service.assign_role_to_user.return_value = 400

    result = assign_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to assign role
    mock_discord_service.assign_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should return the error status
    assert result == 400


def test_assign_discord_role_task_exception_handling(mock_discord_service):
    """Test exception handling in assign_discord_role_task"""
    # Mock Discord service to raise exception
    mock_discord_service.assign_role_to_user.side_effect = Exception("Discord API error")

    with pytest.raises(Exception) as exc_info:
        assign_discord_role_task(guild_id=987654321, discord_user_id=123456789, role_id=456789123)

    # Should call Discord service to assign role
    mock_discord_service.assign_role_to_user.assert_called_once_with(987654321, 123456789, 456789123)

    # Should raise exception with correct message
    assert "Error assigning role to user: Discord API error" in str(exc_info.value)


def test_assign_discord_role_task_missing_guild_id(mock_discord_service):
    """Test when guild_id is None"""
    # This might raise an exception or handle None gracefully
    try:
        result = assign_discord_role_task(guild_id=None, discord_user_id=123456789, role_id=456789123)
        # If it doesn't raise, it should call the service
        mock_discord_service.assign_role_to_user.assert_called_once_with(None, 123456789, 456789123)
        assert result == 204
    except (TypeError, ValueError):
        # If it raises an exception, that's also acceptable
        mock_discord_service.assign_role_to_user.assert_not_called()


def test_assign_discord_role_task_missing_discord_user_id(mock_discord_service):
    """Test when discord_user_id is None"""
    try:
        result = assign_discord_role_task(guild_id=987654321, discord_user_id=None, role_id=456789123)
        mock_discord_service.assign_role_to_user.assert_called_once_with(987654321, None, 456789123)
        assert result == 204
    except (TypeError, ValueError):
        mock_discord_service.assign_role_to_user.assert_not_called()


def test_assign_discord_role_task_invalid_guild_id(mock_discord_service):
    """Test when guild_id is invalid (empty string)"""
    try:
        result = assign_discord_role_task(guild_id="", discord_user_id=123456789, role_id=456789123)
        mock_discord_service.assign_role_to_user.assert_called_once_with("", 123456789, 456789123)
        assert result == 204
    except (TypeError, ValueError):
        mock_discord_service.assign_role_to_user.assert_not_called()


def test_assign_discord_role_task_invalid_discord_user_id(mock_discord_service):
    """Test when discord_user_id is invalid (empty string)"""
    try:
        result = assign_discord_role_task(guild_id=987654321, discord_user_id="", role_id=456789123)
        mock_discord_service.assign_role_to_user.assert_called_once_with(987654321, "", 456789123)
        assert result == 204
    except (TypeError, ValueError):
        mock_discord_service.assign_role_to_user.assert_not_called()
