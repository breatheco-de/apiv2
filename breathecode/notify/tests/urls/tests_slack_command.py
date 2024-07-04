"""
Test /answer
"""

import re, urllib
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import NotifyTestCase
import breathecode.services.slack.commands as commands
from breathecode.services.slack.client import Slack


class NotifyTestSuite(NotifyTestCase):
    """Test /answer"""

    @patch("breathecode.services.slack.client.Slack.__init__", MagicMock(return_value=None))
    @patch("breathecode.services.slack.client.Slack.execute_command", MagicMock(return_value="potato"))
    def test_slack_command___return_correct_value(self):
        """Testing when any other word than the implemented command is entered."""

        url = reverse_lazy("notify:slack_command")
        data = {"text": ""}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = "Processing..."

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Slack.__init__.call_args_list, [call()])
        self.assertEqual(Slack.execute_command.call_args_list, [call(context=data)])

    @patch("breathecode.services.slack.client.Slack.__init__", MagicMock(return_value=None))
    @patch("breathecode.services.slack.client.Slack.execute_command", MagicMock(side_effect=Exception("pokemon")))
    def test_slack_command___raise_exception(self):
        """Testing when exception is prompted."""

        url = reverse_lazy("notify:slack_command")
        data = {"text": ""}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = "Processing..."

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Slack.__init__.call_args_list, [call()])
        self.assertEqual(Slack.execute_command.call_args_list, [call(context=data)])
