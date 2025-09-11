"""
Test cases for revoke_user_discord_permissions and user_has_active_4geeks_plus_plans actions
"""

from unittest.mock import MagicMock, patch

from breathecode.authenticate.models import Cohort, CredentialsDiscord
from breathecode.payments import actions

from ..mixins import PaymentsTestCase


class RevokeUserDiscordPermissionsTestSuite(PaymentsTestCase):
    """Test suite for revoke_user_discord_permissions function"""

    def test_revoke_user_discord_permissions_with_credentials_and_shortcuts(self):
        """Test revoke_user_discord_permissions when user has Discord credentials and cohort has shortcuts"""

        # Mock the Discord service and tasks
        with (
            patch("breathecode.services.discord.Discord") as mock_discord_class,
            patch("breathecode.authenticate.tasks.remove_discord_role_task") as mock_remove_role,
            patch("breathecode.authenticate.tasks.send_discord_dm_task") as mock_send_dm,
        ):

            mock_discord_instance = MagicMock()
            mock_discord_class.return_value = mock_discord_instance

            # Mock Discord API response - user has the role
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"roles": ["987654321"]}
            mock_discord_instance.get_member_in_server.return_value = mock_response

            # Create models
            model = self.bc.database.create(user=1, academy=1, cohort=1, cohort_user=1)

            # Create Discord credentials
            CredentialsDiscord.objects.create(user=model.user, discord_id="123456789", joined_servers=["123456789"])

            # Update cohort with Discord shortcuts
            model.cohort.shortcuts = [{"label": "Discord", "server_id": "123456789", "role_id": "987654321"}]
            model.cohort.save()

            # Call the function
            result = actions.revoke_user_discord_permissions(model.user, model.academy)

            # Verify the task was called
            mock_remove_role.delay.assert_called_once_with("123456789", 123456789, "987654321")

            # Verify DM was sent
            mock_send_dm.delay.assert_called_once_with(123456789, "Your subscription has ended. Role removed.")

            # Verify return value
            self.assertTrue(result)

    def test_revoke_user_discord_permissions_without_credentials(self):
        """Test revoke_user_discord_permissions when user has no Discord credentials"""

        # Create models
        model = self.bc.database.create(user=1, academy=1, cohort=1)

        # Call the function without creating Discord credentials
        result = actions.revoke_user_discord_permissions(model.user, model.academy)

        # Verify return value is False
        self.assertFalse(result)

    def test_revoke_user_discord_permissions_without_shortcuts(self):
        """Test revoke_user_discord_permissions when cohort has no Discord shortcuts"""

        # Mock the Discord service and tasks
        with (
            patch("breathecode.services.discord.Discord") as mock_discord_class,
            patch("breathecode.authenticate.tasks.remove_discord_role_task") as mock_remove_role,
            patch("breathecode.authenticate.tasks.send_discord_dm_task") as mock_send_dm,
        ):

            # Create models
            model = self.bc.database.create(user=1, academy=1, cohort=1, cohort_user=1)

            # Create Discord credentials
            CredentialsDiscord.objects.create(user=model.user, discord_id="123456789", joined_servers=["123456789"])

            # Update cohort without Discord shortcuts
            model.cohort.shortcuts = [{"label": "GitHub", "url": "https://github.com/example"}]
            model.cohort.save()

            # Call the function
            result = actions.revoke_user_discord_permissions(model.user, model.academy)

            # Verify no tasks were called
            mock_remove_role.delay.assert_not_called()
            mock_send_dm.delay.assert_not_called()

            # Verify return value
            self.assertFalse(result)


class UserHasActive4GeeksPlusPlansTestSuite(PaymentsTestCase):
    """Test suite for user_has_active_4geeks_plus_plans function"""

    def test_user_has_active_4geeks_plus_plans_with_no_plans(self):
        """Test user_has_active_4geeks_plus_plans when user has no plans at all"""

        # Create user
        model = self.bc.database.create(user=1)

        # Call the function without creating any plans
        result = actions.user_has_active_4geeks_plus_plans(model.user)

        # Verify return value
        self.assertFalse(result)
