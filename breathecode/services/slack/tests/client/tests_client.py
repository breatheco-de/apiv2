import re, urllib
from django.urls.base import reverse_lazy
from rest_framework import status
from ...client import Slack
from ..mixins import SlackTestCase
import breathecode.services.slack.commands as commands
from ...exceptions import SlackException
from unittest.mock import MagicMock, call, patch
from breathecode.utils import AttrDict

fake_command = AttrDict(**{"fake": AttrDict(**{"execute": MagicMock(return_value="potato")})})


class SlackTestSuite(SlackTestCase):
    """Test /answer"""

    def test_slack_command___not_implemented(self):
        """Testing when command has not been implemented."""

        data = {"text": "simple"}
        slack = Slack()
        with self.assertRaisesMessage(SlackException, "command-does-not-exist"):
            slack.execute_command(data)

    def test_slack_command___no_slack_user(self):
        """Testing when user has no slack_user."""

        data = {"text": "student", "user_id": "name", "team_id": "team", "channel_id": "test"}
        slack = Slack()
        with self.assertRaisesMessage(SlackException, "unauthorized-user"):
            slack.execute_command(data)

    @patch("breathecode.services.slack.client.Slack._execute_command", MagicMock(return_value="some"))
    def test_slack_execute_command___success(self):
        """Testing when execute_command() is successfully executed."""

        data = {"text": "student", "user_id": "name", "team_id": "team", "channel_id": "test"}
        slack = Slack()

        expected = True
        result = slack.execute_command(data)
        self.assertEqual(result, expected)
        self.assertEqual(
            slack._execute_command.call_args_list,
            [
                call(
                    commands,
                    "student",
                    {
                        "users": [],
                        "context": {"text": "student", "user_id": "name", "team_id": "team", "channel_id": "test"},
                    },
                )
            ],
        )

    def test_slack__execute_command__test_executor(self):
        """Testing how execute_command is being executed."""

        data = {"text": "student", "user_id": "name", "team_id": "team", "channel_id": "test"}
        slack = Slack()
        expected = "potato"
        result = slack._execute_command(fake_command, "fake", data)

        self.assertEqual(result, expected)
        self.assertEqual(fake_command.fake.execute.call_args_list, [call(**data)])
