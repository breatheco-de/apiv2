"""
Test cases for grant_discord_roles receiver
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from breathecode.authenticate.models import CredentialsDiscord
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def arange(db, bc: Breathecode, fake):
    yield


def test_grant_discord_roles_with_shortcuts_and_credentials(enable_signals, bc: Breathecode):
    """Test grant_discord_roles when cohort has Discord shortcuts and user has credentials"""
    enable_signals()

    # Mock the assign_discord_role_task to avoid actual API calls
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        mock_assign_role.return_value = None

        # Create user first
        user = bc.database.create(user=1)["user"]

        # Create Discord credentials manually BEFORE creating CohortUser
        CredentialsDiscord.objects.create(user=user, discord_id="123456789", joined_servers=["123456789"])

        # Create cohort with Discord shortcuts
        cohort = bc.database.create(
            cohort={"shortcuts": [{"label": "Discord", "server_id": "123456789", "role_id": "987654321"}]}
        )["cohort"]

        # Create CohortUser (this will trigger the signal)
        cohort_user = bc.database.create(cohort_user={"user": user, "cohort": cohort, "role": "STUDENT"})["cohort_user"]

        # Verify the task was called
        mock_assign_role.assert_called_once_with(
            "123456789", 123456789, "987654321"  # server_id  # discord_user_id (converted to int)  # role_id
        )


def test_grant_discord_roles_without_discord_shortcuts(enable_signals, bc: Breathecode):
    """Test grant_discord_roles when cohort has no Discord shortcuts"""
    enable_signals()

    # Mock the assign_discord_role_task to avoid actual API calls
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        # Create user first
        user = bc.database.create(user=1)["user"]

        # Create Discord credentials manually BEFORE creating CohortUser
        CredentialsDiscord.objects.create(user=user, discord_id="123456789", joined_servers=["123456789"])

        # Create cohort without Discord shortcuts
        cohort = bc.database.create(cohort={"shortcuts": [{"label": "GitHub", "url": "https://github.com/example"}]})[
            "cohort"
        ]

        # Create CohortUser (this will trigger the signal)
        cohort_user = bc.database.create(cohort_user={"user": user, "cohort": cohort, "role": "STUDENT"})["cohort_user"]

        # Verify the task was NOT called
        mock_assign_role.assert_not_called()


def test_grant_discord_roles_without_credentials(enable_signals, bc: Breathecode):
    """Test grant_discord_roles when user has no Discord credentials"""
    enable_signals()

    # Mock the assign_discord_role_task to avoid actual API calls
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        # Create models with Discord shortcuts but no credentials
        model = bc.database.create(
            user=1,
            cohort_user={"role": "STUDENT"},
            cohort={"shortcuts": [{"label": "Discord", "server_id": "123456789", "role_id": "987654321"}]},
        )

        # Verify the task was NOT called
        mock_assign_role.assert_not_called()


def test_grant_discord_roles_without_shortcuts(enable_signals, bc: Breathecode):
    """Test grant_discord_roles when cohort has no shortcuts at all"""
    enable_signals()

    # Mock the assign_discord_role_task to avoid actual API calls
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        # Create user first
        user = bc.database.create(user=1)["user"]

        # Create Discord credentials manually BEFORE creating CohortUser
        CredentialsDiscord.objects.create(user=user, discord_id="123456789", joined_servers=["123456789"])

        # Create cohort without any shortcuts
        cohort = bc.database.create(cohort={})["cohort"]

        # Create CohortUser (this will trigger the signal)
        cohort_user = bc.database.create(cohort_user={"user": user, "cohort": cohort, "role": "STUDENT"})["cohort_user"]

        # Verify the task was NOT called
        mock_assign_role.assert_not_called()


def test_grant_discord_roles_multiple_shortcuts(enable_signals, bc: Breathecode):
    """Test grant_discord_roles with multiple shortcuts including Discord"""
    enable_signals()

    # Mock the assign_discord_role_task to avoid actual API calls
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        mock_assign_role.return_value = None

        # Create user first
        user = bc.database.create(user=1)["user"]

        # Create Discord credentials manually BEFORE creating CohortUser
        CredentialsDiscord.objects.create(user=user, discord_id="123456789", joined_servers=["123456789"])

        # Create cohort with multiple shortcuts including Discord
        cohort = bc.database.create(
            cohort={
                "shortcuts": [
                    {"label": "GitHub", "url": "https://github.com/example"},
                    {"label": "Discord", "server_id": "123456789", "role_id": "987654321"},
                    {"label": "Slack", "channel": "#general"},
                ]
            }
        )["cohort"]

        # Create CohortUser (this will trigger the signal)
        cohort_user = bc.database.create(cohort_user={"user": user, "cohort": cohort, "role": "STUDENT"})["cohort_user"]

        # Verify the task was called only once for the Discord shortcut
        mock_assign_role.assert_called_once_with(
            "123456789", 123456789, "987654321"  # server_id  # discord_user_id (converted to int)  # role_id
        )


def test_grant_discord_roles_with_exception(enable_signals, bc: Breathecode):
    """Test grant_discord_roles when assign_discord_role_task raises an exception"""
    enable_signals()

    # Mock the assign_discord_role_task to raise an exception
    with patch("breathecode.authenticate.tasks.assign_discord_role_task") as mock_assign_role:
        mock_assign_role.side_effect = Exception("Discord API error")

        # Create user first
        user = bc.database.create(user=1)["user"]

        # Create Discord credentials manually BEFORE creating CohortUser
        CredentialsDiscord.objects.create(user=user, discord_id="123456789", joined_servers=["123456789"])

        # Create cohort with Discord shortcuts
        cohort = bc.database.create(
            cohort={"shortcuts": [{"label": "Discord", "server_id": "123456789", "role_id": "987654321"}]}
        )["cohort"]

        # Create CohortUser (this will trigger the signal)
        cohort_user = bc.database.create(cohort_user={"user": user, "cohort": cohort, "role": "STUDENT"})["cohort_user"]

        # Verify the task was called despite the exception
        mock_assign_role.assert_called_once_with(
            "123456789", 123456789, "987654321"  # server_id  # discord_user_id (converted to int)  # role_id
        )
