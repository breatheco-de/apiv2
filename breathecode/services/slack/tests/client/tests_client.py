import re, urllib
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..client import Slack
from .mixins import SlackTestCase
import breathecode.services.slack.commands as commands
from ..exceptions import SlackException


class SlackTestSuite(SlackTestCase):
    """Test /answer"""
    def test_slack_command___not_implemented(self):
        """Testing when command has not been implemented."""

        data = {'text': 'simple'}
        slack = Slack()
        with self.assertRaisesMessage(SlackException, 'command-does-not-exist'):
            slack.execute_command(data)

    def test_slack_command___no_slack_user(self):
        """Testing when user has no slack_user."""

        data = {'text': 'student', 'user_id': 'name', 'team_id': 'team', 'channel_id': 'test'}
        slack = Slack()
        with self.assertRaisesMessage(SlackException, 'unauthorized-user'):
            slack.execute_command(data)


#    @patch('breathecode.services.slack.commands.madeup_name.execute', MagicMock(return_value=) )
#     def test_command

#     self.assertEqual(commands.madeup_name.execute.call_args_list,[call(data)])
