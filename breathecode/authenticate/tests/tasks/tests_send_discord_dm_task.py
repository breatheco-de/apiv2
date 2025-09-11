"""
Test cases for send_discord_dm_task
"""

import logging
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.tasks import send_discord_dm_task


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


@pytest.fixture
def mock_discord_service():
    """Mock Discord service with send_dm_to_user method"""
    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_instance = MagicMock()
        mock_discord_class.return_value = mock_instance

        yield mock_instance


def test_send_discord_dm_task_successful_send_200(mock_discord_service):
    """Test successful DM send with 200 status code"""
    with patch("breathecode.authenticate.tasks.asyncio.run") as mock_asyncio_run:
        mock_asyncio_run.return_value = 200

        result = send_discord_dm_task(discord_user_id=123456789, message="Test message")

        # Should call Discord service to send DM
        mock_discord_service.send_dm_to_user.assert_called_once_with(123456789, "Test message")

        # Should return 200
        assert result == 200

        # Should log success
        assert "DM sent successfully" in str(logging.Logger.info.call_args_list[0])


def test_send_discord_dm_task_channel_not_found_204(mock_discord_service):
    """Test when DM channel is not found (204 status)"""
    with patch("breathecode.authenticate.tasks.asyncio.run") as mock_asyncio_run:
        mock_asyncio_run.return_value = 204

        result = send_discord_dm_task(discord_user_id=123456789, message="Test message")

        # Should call Discord service to send DM
        mock_discord_service.send_dm_to_user.assert_called_once_with(123456789, "Test message")

        # Should return 204
        assert result == 204

        # Should log channel not found
        assert "Channel not found" in str(logging.Logger.info.call_args_list[0])


def test_send_discord_dm_task_exception_handling(mock_discord_service):
    """Test exception handling in send_discord_dm_task"""
    # Mock Discord service to raise exception
    mock_discord_service.send_dm_to_user.side_effect = Exception("Discord API error")

    with pytest.raises(AbortTask) as exc_info:
        send_discord_dm_task(discord_user_id=123456789, message="Test message")

    # Should call Discord service to send DM
    mock_discord_service.send_dm_to_user.assert_called_once_with(123456789, "Test message")

    # Should raise AbortTask with correct message
    assert "Error sending DM: Discord API error" in str(exc_info.value)
