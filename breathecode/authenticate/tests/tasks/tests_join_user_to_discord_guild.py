from unittest.mock import MagicMock, patch

import pytest

from breathecode.tests.mixins.breathecode_mixin import Breathecode


@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch: pytest.MonkeyPatch, db):
    mock_assign_task = MagicMock()
    monkeypatch.setattr("breathecode.authenticate.tasks.assign_discord_role_task.delay", mock_assign_task)
    yield mock_assign_task


@pytest.fixture(autouse=True)
def mock_save_credentials(monkeypatch: pytest.MonkeyPatch, db):
    mock_save = MagicMock(return_value=True)
    monkeypatch.setattr("breathecode.authenticate.actions.save_discord_credentials", mock_save)
    yield mock_save


@pytest.fixture
def mock_discord_service():
    with patch("breathecode.authenticate.tasks.Discord") as mock_discord_class:
        mock_discord_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_discord_instance.join_user_to_guild.return_value = mock_response
        mock_discord_class.return_value = mock_discord_instance
        yield mock_discord_instance


def test_successful_join_user_to_discord_guild(
    mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode
):
    """Test successful user join to Discord guild with role assignment"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}],
        },
    )

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.cohort_user.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort",
    )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were saved
    mock_save_credentials.assert_called_once_with(
        user_id=model.cohort_user.user.id, discord_user_id=123456789, guild_id="987654321", cohort_slug="test-cohort"
    )

    # Verify role assignment task was called
    mock_celery_tasks.assert_called_once_with(
        guild_id="987654321", discord_user_id=123456789, role_id="456789123", academy_id=1
    )

    # Verify task returns None
    assert result is None


def test_join_user_already_in_guild(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test user already in Discord guild (status 204) - should assign roles without saving credentials"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}],
        },
    )

    # Mock Discord service to return status 204 (user already in guild)
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_discord_service.join_user_to_guild.return_value = mock_response

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.cohort_user.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort",
    )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were NOT saved (user already in guild)
    mock_save_credentials.assert_not_called()

    # Verify role assignment task was called
    mock_celery_tasks.assert_called_once_with(
        guild_id="987654321", discord_user_id=123456789, role_id="456789123", academy_id=1
    )


def test_cohort_not_found(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when cohort with given slug is not found"""
    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=1, access_token="test_access_token", discord_user_id=123456789, cohort_slug="non-existent-cohort"
    )

    # Verify Discord service was NOT called
    mock_discord_service.join_user_to_guild.assert_not_called()

    # Verify credentials were NOT saved
    mock_save_credentials.assert_not_called()

    # Verify role assignment task was NOT called
    mock_celery_tasks.assert_not_called()

    # Verify task returns None
    assert result is None


def test_no_discord_shortcuts(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when cohort has no Discord shortcuts"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Slack", "server_id": "123456789", "role_id": "987654321"}],
        },
    )

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.cohort_user.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort",
    )

    # Verify Discord service was NOT called
    mock_discord_service.join_user_to_guild.assert_not_called()

    # Verify credentials were NOT saved
    mock_save_credentials.assert_not_called()

    # Verify role assignment task was NOT called
    mock_celery_tasks.assert_not_called()


def test_multiple_roles_assignment(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test assignment of multiple roles from different cohorts"""
    # Create test data with multiple cohorts having Discord shortcuts
    model = bc.database.create(
        user=1,
        cohort=[
            {
                "slug": "test-cohort-1",
                "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "111111111"}],
            },
            {
                "slug": "test-cohort-2",
                "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "222222222"}],
            },
        ],
        academy=1,
    )

    # Create cohort_users after model is created
    bc.database.create(
        cohort_user=[
            {"user": model.user, "cohort": model.cohort[0], "role": "STUDENT", "academy": model.academy},
            {"user": model.user, "cohort": model.cohort[1], "role": "STUDENT", "academy": model.academy},
        ]
    )

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort-1",
    )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were saved
    mock_save_credentials.assert_called_once_with(
        user_id=model.user.id, discord_user_id=123456789, guild_id="987654321", cohort_slug="test-cohort-1"
    )

    # Verify both role assignment tasks were called
    assert mock_celery_tasks.call_count == 2
    mock_celery_tasks.assert_any_call(
        guild_id="987654321", discord_user_id=123456789, role_id="111111111", academy_id=1
    )
    mock_celery_tasks.assert_any_call(
        guild_id="987654321", discord_user_id=123456789, role_id="222222222", academy_id=1
    )


def test_discord_service_exception(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when Discord service raises an exception"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}],
        },
    )

    # Mock Discord service to raise an exception
    mock_discord_service.join_user_to_guild.side_effect = Exception("Discord API error")

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    # Verify that the task raises an exception
    with pytest.raises(Exception, match="Discord API error"):
        join_user_to_discord_guild(
            user_id=model.cohort_user.user.id,
            access_token="test_access_token",
            discord_user_id=123456789,
            cohort_slug="test-cohort",
        )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were NOT saved
    mock_save_credentials.assert_not_called()

    # Verify role assignment task was NOT called
    mock_celery_tasks.assert_not_called()


def test_unexpected_join_status(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when Discord service returns unexpected status code"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}],
        },
    )

    # Mock Discord service to return unexpected status code
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_discord_service.join_user_to_guild.return_value = mock_response

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    # Verify that the task raises an exception
    with pytest.raises(Exception, match="Failed to join Discord guild:"):
        join_user_to_discord_guild(
            user_id=model.cohort_user.user.id,
            access_token="test_access_token",
            discord_user_id=123456789,
            cohort_slug="test-cohort",
        )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were NOT saved
    mock_save_credentials.assert_not_called()

    # Verify role assignment task was NOT called
    mock_celery_tasks.assert_not_called()


def test_save_credentials_failure(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when save_discord_credentials returns False"""
    # Create cohort_user directly (this automatically creates user, cohort, academy)
    model = bc.database.create(
        cohort_user=1,
        cohort={
            "slug": "test-cohort",
            "shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}],
        },
    )

    # Mock save_credentials to return False
    mock_save_credentials.return_value = False

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.cohort_user.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort",
    )

    # Verify Discord service was called
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="987654321", discord_user_id=123456789
    )

    # Verify credentials were saved
    mock_save_credentials.assert_called_once_with(
        user_id=model.cohort_user.user.id, discord_user_id=123456789, guild_id="987654321", cohort_slug="test-cohort"
    )

    # Verify role assignment task was NOT called (because save failed)
    mock_celery_tasks.assert_not_called()


def test_inconsistent_server_ids(mock_discord_service, mock_celery_tasks, mock_save_credentials, bc: Breathecode):
    """Test when cohorts have different server_ids (should only use the first one)"""
    # Create test data with different server_ids
    model = bc.database.create(
        user=1,
        cohort=[
            {
                "slug": "test-cohort-1",
                "shortcuts": [{"label": "Discord", "server_id": "111111111", "role_id": "111111111"}],
            },
            {
                "slug": "test-cohort-2",
                "shortcuts": [{"label": "Discord", "server_id": "222222222", "role_id": "222222222"}],
            },
        ],
        academy=1,
    )

    # Create cohort_users after model is created
    bc.database.create(
        cohort_user=[
            {"user": model.user, "cohort": model.cohort[0], "role": "STUDENT", "academy": model.academy},
            {"user": model.user, "cohort": model.cohort[1], "role": "STUDENT", "academy": model.academy},
        ]
    )

    # Import and call the task
    from breathecode.authenticate.tasks import join_user_to_discord_guild

    result = join_user_to_discord_guild(
        user_id=model.user.id,
        access_token="test_access_token",
        discord_user_id=123456789,
        cohort_slug="test-cohort-1",
    )

    # Verify Discord service was called with the first server_id
    mock_discord_service.join_user_to_guild.assert_called_once_with(
        access_token="test_access_token", guild_id="111111111", discord_user_id=123456789
    )

    # Verify credentials were saved with the first server_id
    mock_save_credentials.assert_called_once_with(
        user_id=model.user.id,
        discord_user_id=123456789,
        guild_id="111111111",
        cohort_slug="test-cohort-1",
    )

    # Verify only the role from the first cohort was assigned
    mock_celery_tasks.assert_called_once_with(
        guild_id="111111111", discord_user_id=123456789, role_id="111111111", academy_id=1
    )
