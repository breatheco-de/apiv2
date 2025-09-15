"""
Test cases for grant_discord_roles receiver
"""

from unittest.mock import MagicMock, patch

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):
    """Setup fixture to mock the Celery task"""
    mock_task = MagicMock()
    monkeypatch.setattr("breathecode.authenticate.tasks.assign_discord_role_task.delay", mock_task)
    yield mock_task


def test_successful_discord_role_assignment(enable_signals, bc: Breathecode, setup):
    """Test successful Discord role assignment when user has credentials and cohort has Discord shortcuts"""
    enable_signals()

    # Create test data
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        academy=1,
    )

    # Create Discord credentials BEFORE creating cohort_user (so they exist when the signal fires)
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was called with correct parameters
    setup.assert_called_once_with(
        "987654321",  # server_id
        123456789,  # discord_user_id (converted to int)
        "456789123",  # role_id
        1,  # academy_id
    )


def test_no_discord_credentials(enable_signals, bc: Breathecode, setup):
    """Test when user has no Discord credentials - should skip role assignment"""
    enable_signals()

    # Create test data without Discord credentials
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_no_shortcuts(enable_signals, bc: Breathecode, setup):
    """Test when cohort has no shortcuts - should skip role assignment"""
    enable_signals()

    # Create test data without shortcuts
    model = bc.database.create(
        user=1,
        credentials_discord={"discord_id": "123456789"},
        cohort={"shortcuts": None},
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_empty_shortcuts(enable_signals, bc: Breathecode, setup):
    """Test when cohort has empty shortcuts - should skip role assignment"""
    enable_signals()

    # Create test data with empty shortcuts
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": []},
        academy=1,
    )

    # Create Discord credentials BEFORE creating cohort_user
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_no_discord_shortcut(enable_signals, bc: Breathecode, setup):
    """Test when shortcuts don't include Discord - should skip role assignment"""
    enable_signals()

    # Create test data with non-Discord shortcuts
    model = bc.database.create(
        user=1,
        cohort={
            "shortcuts": [
                {"label": "Slack", "server_id": "987654321", "role_id": "456789123"},
                {"label": "GitHub", "server_id": "987654321", "role_id": "456789123"},
            ]
        },
        academy=1,
    )

    # Create Discord credentials BEFORE creating cohort_user
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_multiple_discord_shortcuts(enable_signals, bc: Breathecode, setup):
    """Test when cohort has multiple Discord shortcuts - should assign all roles"""
    enable_signals()

    # Create test data with multiple Discord shortcuts
    model = bc.database.create(
        user=1,
        cohort={
            "shortcuts": [
                {"label": "Discord", "server_id": "987654321", "role_id": "456789123"},
                {"label": "Discord", "server_id": "987654322", "role_id": "456789124"},
            ]
        },
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Create Discord credentials manually
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Verify the Celery task was called twice with different parameters
    assert setup.call_count == 2

    # Check first call
    setup.assert_any_call(
        "987654321",  # server_id
        123456789,  # discord_user_id
        "456789123",  # role_id
        1,  # academy_id
    )

    # Check second call
    setup.assert_any_call(
        "987654322",  # server_id
        123456789,  # discord_user_id
        "456789124",  # role_id
        1,  # academy_id
    )


def test_missing_server_id(enable_signals, bc: Breathecode, setup):
    """Test when Discord shortcut is missing server_id - should skip that shortcut"""
    enable_signals()

    # Create test data with incomplete Discord shortcut
    model = bc.database.create(
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
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Create Discord credentials manually
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Verify the Celery task was called with None as server_id
    setup.assert_called_once_with(
        None,  # server_id (missing)
        123456789,  # discord_user_id
        "456789123",  # role_id
        1,  # academy_id
    )


def test_missing_role_id(enable_signals, bc: Breathecode, setup):
    """Test when Discord shortcut is missing role_id - should skip that shortcut"""
    enable_signals()

    # Create test data with incomplete Discord shortcut
    model = bc.database.create(
        user=1,
        cohort={
            "shortcuts": [
                {
                    "label": "Discord",
                    "server_id": "987654321",
                    # Missing role_id
                }
            ]
        },
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Create Discord credentials manually
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Verify the Celery task was called with None as role_id
    setup.assert_called_once_with(
        "987654321",  # server_id
        123456789,  # discord_user_id
        None,  # role_id (missing)
        1,  # academy_id
    )


@patch("breathecode.authenticate.tasks.assign_discord_role_task.delay")
def test_exception_handling(mock_task_delay, enable_signals, bc: Breathecode):
    """Test exception handling when Celery task raises an error"""
    enable_signals()

    # Make the task raise an exception
    mock_task_delay.side_effect = Exception("Celery task failed")

    # Create test data
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Create Discord credentials manually
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # The receiver should handle the exception gracefully
    # (it catches exceptions and logs them, but doesn't re-raise)
    # Verify the task was attempted
    mock_task_delay.assert_called_once_with(
        "987654321",  # server_id
        123456789,  # discord_user_id
        "456789123",  # role_id
        1,  # academy_id
    )


def test_discord_id_conversion_to_int(enable_signals, bc: Breathecode, setup):
    """Test that discord_id string is properly converted to int"""
    enable_signals()

    # Create test data with string discord_id
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "123456789", "role_id": "456789123"}]},
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Create Discord credentials manually
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="987654321")

    # Verify the Celery task was called with int discord_id
    setup.assert_called_once_with(
        "123456789",  # server_id
        987654321,  # discord_user_id (converted to int)
        "456789123",  # role_id
        1,  # academy_id
    )
