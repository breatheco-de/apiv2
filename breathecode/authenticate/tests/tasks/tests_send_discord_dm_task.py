"""
Test cases for send_discord_dm_task
"""

from unittest.mock import MagicMock, patch

import pytest
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.tasks import send_discord_dm_task
from breathecode.tests.mixins.breathecode_mixin import Breathecode


def test_send_discord_dm_task_success(bc: Breathecode, db):
    """Test successful DM sending returns 200"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.asyncio.run") as mock_asyncio_run,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.send_dm_to_user.return_value = "mock_coroutine"
        mock_discord_class.return_value = mock_discord_service
        mock_asyncio_run.return_value = 200

        result = send_discord_dm_task(discord_user_id=67890, message="Hello from 4Geeks!", academy_id=model.academy.id)

        mock_discord_class.assert_called_once_with(academy_id=model.academy.id)

        mock_discord_service.send_dm_to_user.assert_called_once_with(67890, "Hello from 4Geeks!")

        mock_asyncio_run.assert_called_once_with("mock_coroutine")

        # Verify task returns success code
        assert result == 200


def test_send_discord_dm_task_channel_not_found(bc: Breathecode, db):
    """Test when Discord API returns 204 - channel not found"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.asyncio.run") as mock_asyncio_run,
        patch("logging.Logger.info") as mock_logger_info,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.send_dm_to_user.return_value = "mock_coroutine"
        mock_discord_class.return_value = mock_discord_service
        mock_asyncio_run.return_value = 204  # Channel not found

        result = send_discord_dm_task(discord_user_id=67890, message="Hello from 4Geeks!", academy_id=model.academy.id)

        # Verify Discord service was called
        mock_discord_service.send_dm_to_user.assert_called_once_with(67890, "Hello from 4Geeks!")

        # Verify correct log message
        mock_logger_info.assert_called_with("Channel not found")

        # Verify task returns 204 (channel not found)
        assert result == 204


def test_send_discord_dm_task_api_error_other_codes(bc: Breathecode, db):
    """Test when Discord API returns other error codes - should not return anything"""
    model = bc.database.create(academy=1)

    with (
        patch("breathecode.authenticate.tasks.Discord") as mock_discord_class,
        patch("breathecode.authenticate.tasks.asyncio.run") as mock_asyncio_run,
    ):
        mock_discord_service = MagicMock()
        mock_discord_service.send_dm_to_user.return_value = "mock_coroutine"
        mock_discord_class.return_value = mock_discord_service
        mock_asyncio_run.return_value = 403  # Forbidden

        result = send_discord_dm_task(discord_user_id=67890, message="Hello from 4Geeks!", academy_id=model.academy.id)

        # Verify Discord service was called
        mock_discord_service.send_dm_to_user.assert_called_once_with(67890, "Hello from 4Geeks!")

        # Task doesn't explicitly handle other codes, so returns None
        assert result is None
