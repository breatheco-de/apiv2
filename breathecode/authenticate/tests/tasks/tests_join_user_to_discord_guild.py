"""
Test cases for join_user_to_discord_guild task
"""

import logging
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest

from breathecode.authenticate.tasks import join_user_to_discord_guild


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("logging.Logger.debug", MagicMock())
    yield


@pytest.fixture
def mock_discord_service():
    """Mock Discord service with join_user_to_guild method"""
    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_instance = MagicMock()
        mock_discord_class.return_value = mock_instance

        # Mock successful join (201 status)
        mock_join_response = MagicMock()
        mock_join_response.status_code = 201
        mock_instance.join_user_to_guild.return_value = mock_join_response

        yield mock_instance


@pytest.fixture
def mock_save_discord_credentials():
    """Mock save_discord_credentials function"""
    with patch("breathecode.authenticate.actions.save_discord_credentials") as mock_save:
        mock_save.return_value = True
        yield mock_save


@pytest.fixture
def mock_assign_role_task():
    """Mock assign_discord_role_task"""
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign:
        mock_assign.delay.return_value = None
        yield mock_assign


@pytest.fixture
def mock_join_task():
    """Mock the join_user_to_discord_guild task to avoid calling real Celery task"""
    with patch("breathecode.authenticate.tasks.join_user_to_discord_guild") as mock_task:
        mock_task.delay.return_value = None
        yield mock_task


def test_join_user_to_discord_guild_no_cohorts(database: capy.Database, mock_discord_service, mock_join_task):
    """Test join_user_to_discord_guild when user has no cohorts"""
    # Create user without cohorts
    model = database.create(user=1)

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug="test-cohort",
    )

    # Should not call Discord service since no cohorts found
    assert mock_discord_service.join_user_to_guild.call_count == 0


def test_join_user_to_discord_guild_no_discord_shortcuts(database: capy.Database, mock_discord_service, mock_join_task):
    """Test join_user_to_discord_guild when cohort has no Discord shortcuts"""
    # Create user with cohort that has Discord shortcuts
    model = database.create(
        user=1,
        cohort={"shortcuts": [{"label": "GitHub", "server_id": "12345"}]},
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should not call Discord service since no Discord shortcuts
    assert mock_discord_service.join_user_to_guild.call_count == 0


def test_join_user_to_discord_guild_successful_join_201(
    database: capy.Database, mock_discord_service, mock_save_discord_credentials, mock_assign_role_task, mock_join_task
):
    """Test successful join with 201 status code"""
    # Create user with cohort that has Discord shortcut
    model = database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should call Discord service to join
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        user_id=model.user.id,
        access_token="test_token",
        guild_id="987654321",
        discord_user_id="123456789",
        role_id="456789123",
        is_suscriber=True,
    )

    # Should save credentials
    mock_save_discord_credentials.assert_called_once_with(
        user_id=model.user.id,
        discord_user_id="123456789",
        guild_id="987654321",
        role_id="456789123",
        cohort_slug=model.cohort.slug,
    )

    # Should assign role
    mock_assign_role_task.delay.assert_called_once_with(
        guild_id="987654321", discord_user_id="123456789", role_id="456789123"
    )


def test_join_user_to_discord_guild_already_in_server_204(
    database: capy.Database, mock_discord_service, mock_assign_role_task, mock_join_task
):
    """Test when user is already in server (204 status)"""
    # Mock 204 response (already in server)
    mock_join_response = MagicMock()
    mock_join_response.status_code = 204
    mock_discord_service.join_user_to_guild.return_value = mock_join_response

    # Create user with cohort that has Discord shortcut
    model = database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should still assign role even if already in server
    mock_assign_role_task.delay.assert_called_once_with(
        guild_id="987654321", discord_user_id="123456789", role_id="456789123"
    )


def test_join_user_to_discord_guild_join_failed(database: capy.Database, mock_discord_service, mock_join_task):
    """Test when Discord join fails"""
    # Mock failed join response
    mock_join_response = MagicMock()
    mock_join_response.status_code = 400
    mock_discord_service.join_user_to_guild.return_value = mock_join_response

    # Create user with cohort that has Discord shortcut
    model = database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should handle the failed join gracefully


def test_join_user_to_discord_guild_multiple_cohorts(
    database: capy.Database, mock_discord_service, mock_save_discord_credentials, mock_assign_role_task, mock_join_task
):
    """Test with multiple cohorts having Discord shortcuts"""
    # Create user with multiple cohorts
    model = database.create(
        user=1,
        cohort=[
            {"shortcuts": [{"label": "Discord", "server_id": "111111111", "role_id": "222222222"}]},
            {"shortcuts": [{"label": "Discord", "server_id": "333333333", "role_id": "444444444"}]},
        ],
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort[0].slug,  # Use first cohort slug
    )

    # Should call Discord service once (for the cohort specified by cohort_slug)
    assert mock_discord_service.join_user_to_guild.call_count == 1

    # Should save credentials once
    assert mock_save_discord_credentials.call_count == 1

    # Should assign role once
    assert mock_assign_role_task.delay.call_count == 1


def test_join_user_to_discord_guild_exception_handling(database: capy.Database, mock_discord_service, mock_join_task):
    """Test exception handling in join_user_to_discord_guild"""
    # Mock Discord service to raise exception
    mock_discord_service.join_user_to_guild.side_effect = Exception("Discord API error")

    # Create user with cohort that has Discord shortcut
    model = database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should handle the exception gracefully


def test_join_user_to_discord_guild_no_server_id(database: capy.Database, mock_discord_service, mock_join_task):
    """Test when Discord shortcut has no server_id"""
    # Create user with cohort that has Discord shortcut but no server_id
    model = database.create(
        user=1,
        cohort={
            "shortcuts": [
                {
                    "label": "Discord",
                    "role_id": "456789123",
                    # Missing server_id
                }
            ]
        },
        cohort_user=1,
        academy=1,
        city=1,
        country=1,
    )

    # Call the task function directly (not through Celery)
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_token",
        discord_user_id="123456789",
        is_suscriber=True,
        cohort_slug=model.cohort.slug,
    )

    # Should not call Discord service since server_id is None
    assert mock_discord_service.join_user_to_guild.call_count == 0
