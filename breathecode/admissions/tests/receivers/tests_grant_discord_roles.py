"""
Test cases for grant_discord_roles receiver
"""

from unittest.mock import MagicMock, patch

import capyc.pytest as capy
import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):
    """Setup fixture to mock the Celery task"""
    mock_task = MagicMock()
    monkeypatch.setattr("breathecode.authenticate.tasks.assign_discord_role_task.delay", mock_task)
    yield mock_task


def test_successful_discord_role_assignment(signals: capy.Signals, bc: Breathecode, setup):
    """Test successful Discord role assignment when user has credentials and cohort has Discord shortcuts"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

    # Create test data
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        academy=1,
    )
    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was called with correct parameters
    setup.assert_called_once_with(
        "987654321",  # server_id (string as passed from receiver)
        123456789,  # discord_user_id (converted to int)
        "456789123",  # role_id (string as passed from receiver)
        1,  # academy_id
    )


def test_no_discord_credentials(signals: capy.Signals, bc: Breathecode, setup):
    """Test when user has no Discord credentials - should skip role assignment"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

    # Create test data without Discord credentials
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": [{"label": "Discord", "server_id": "987654321", "role_id": "456789123"}]},
        cohort_user={"role": "STUDENT"},
        academy=1,
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_no_shortcuts(signals: capy.Signals, bc: Breathecode, setup):
    """Test when cohort has no shortcuts - should skip role assignment"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

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


def test_empty_shortcuts(signals: capy.Signals, bc: Breathecode, setup):
    """Test when cohort has empty shortcuts - should skip role assignment"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

    # Create test data with empty shortcuts
    model = bc.database.create(
        user=1,
        cohort={"shortcuts": []},
        academy=1,
    )

    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_no_discord_shortcut(signals: capy.Signals, bc: Breathecode, setup):
    """Test when shortcuts don't include Discord - should skip role assignment"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

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

    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was NOT called
    setup.assert_not_called()


def test_multiple_discord_shortcuts(signals: capy.Signals, bc: Breathecode, setup):
    """Test when cohort has multiple Discord shortcuts - should assign all roles"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

    # Create test data with multiple Discord shortcuts
    model = bc.database.create(
        user=1,
        cohort={
            "shortcuts": [
                {"label": "Discord", "server_id": "987654321", "role_id": "456789123"},
                {"label": "Discord", "server_id": "987654322", "role_id": "456789124"},
            ]
        },
        academy=1,
    )

    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was called twice with different parameters
    assert setup.call_count == 2

    # Check first call
    setup.assert_any_call(
        "987654321",  # server_id (string as passed from receiver)
        123456789,  # discord_user_id
        "456789123",  # role_id (string as passed from receiver)
        1,  # academy_id
    )

    # Check second call
    setup.assert_any_call(
        "987654322",  # server_id (string as passed from receiver)
        123456789,  # discord_user_id
        "456789124",  # role_id (string as passed from receiver)
        1,  # academy_id
    )


def test_missing_server_id(signals: capy.Signals, bc: Breathecode, setup):
    """Test when Discord shortcut is missing server_id - should skip that shortcut"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

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
        academy=1,
    )

    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was called with None as server_id
    setup.assert_called_once_with(
        None,  # server_id (missing)
        123456789,  # discord_user_id
        "456789123",  # role_id
        1,  # academy_id
    )


def test_missing_role_id(signals: capy.Signals, bc: Breathecode, setup):
    """Test when Discord shortcut is missing role_id - should skip that shortcut"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

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
        academy=1,
    )

    from breathecode.authenticate.models import CredentialsDiscord

    CredentialsDiscord.objects.create(user=model.user, discord_id="123456789")

    # Now create cohort_user, which will trigger the signal
    bc.database.create(
        cohort_user={"user": model.user, "cohort": model.cohort, "role": "STUDENT", "academy": model.academy}
    )

    # Verify the Celery task was called with None as role_id
    setup.assert_called_once_with(
        "987654321",  # server_id
        123456789,  # discord_user_id
        None,  # role_id (missing)
        1,  # academy_id
    )


def test_mixed_shortcuts_with_incomplete_discord_data(signals: capy.Signals, bc: Breathecode, setup):
    """Test when cohort has 5 shortcuts: 3 non-Discord, 2 Discord (1 complete, 1 incomplete) - should call task only 2 times"""
    signals.enable("breathecode.admissions.signals.cohort_user_created")

    # Create test data with mixed shortcuts
    model = bc.database.create(
        user=1,
        cohort={
            "shortcuts": [
                # Non-Discord shortcuts (should be ignored)
                {"label": "Slack", "server_id": "slack123", "role_id": "slack_role"},
                {"label": "GitHub", "server_id": "github123", "role_id": "github_role"},
                {"label": "Zoom", "server_id": "zoom123", "role_id": "zoom_role"},
                # Discord shortcuts
                {"label": "Discord", "server_id": "987654321", "role_id": "456789123"},  # Complete
                {"label": "Discord", "server_id": "987654322", "role_id": None},  # Missing role_id
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

    # Verify the Celery task was called exactly 2 times (only for Discord shortcuts)
    assert setup.call_count == 2

    # Check first call (complete Discord shortcut)
    setup.assert_any_call(
        "987654321",  # server_id
        123456789,  # discord_user_id
        "456789123",  # role_id
        1,  # academy_id
    )

    # Check second call (incomplete Discord shortcut with missing role_id)
    setup.assert_any_call(
        "987654322",  # server_id
        123456789,  # discord_user_id
        None,  # role_id (missing)
        1,  # academy_id
    )
