"""
Test /answer
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, call, patch
from django.http.request import HttpRequest
from ..mixins import FeedbackTestCase
from ...admin import send_bulk_survey
from ... import actions

from django.contrib.messages import api


class SendSurveyTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 With zero User
    """

    @patch("django.contrib.messages.api.add_message", MagicMock())
    @patch("breathecode.feedback.actions.send_question", MagicMock())
    def test_with_zero_users(self):
        request = HttpRequest()
        User = self.bc.database.get_model("auth.User")

        queryset = User.objects.all()
        result = send_bulk_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("auth.User"), [])

        self.assertEqual(
            api.add_message.call_args_list,
            [
                call(request, 25, "Survey was successfully sent", extra_tags="", fail_silently=False),
            ],
        )
        self.assertEqual(actions.send_question.call_args_list, [])

    """
    🔽🔽🔽 With two User
    """

    @patch("django.contrib.messages.api.add_message", MagicMock())
    @patch("breathecode.feedback.actions.send_question", MagicMock())
    def test_with_two_users(self):
        request = HttpRequest()
        User = self.bc.database.get_model("auth.User")

        model = self.bc.database.create(user=2)
        db = self.bc.format.to_dict(model.user)

        queryset = User.objects.all()
        result = send_bulk_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("auth.User"), db)

        self.assertEqual(
            api.add_message.call_args_list,
            [
                call(request, 25, "Survey was successfully sent", extra_tags="", fail_silently=False),
            ],
        )
        self.assertEqual(actions.send_question.call_args_list, [call(model.user[0]), call(model.user[1])])

    """
    🔽🔽🔽 With two User raise exceptions
    """

    @patch("django.contrib.messages.api.add_message", MagicMock())
    @patch("breathecode.feedback.actions.send_question", MagicMock(side_effect=Exception("qwerty")))
    @patch("logging.Logger.fatal", MagicMock())
    def test_with_two_users__raises_exceptions__same_exception(self):
        request = HttpRequest()
        User = self.bc.database.get_model("auth.User")

        model = self.bc.database.create(user=2)
        db = self.bc.format.to_dict(model.user)

        queryset = User.objects.all()
        result = send_bulk_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("auth.User"), db)

        self.assertEqual(actions.send_question.call_args_list, [call(model.user[0]), call(model.user[1])])
        self.assertEqual(
            api.add_message.call_args_list,
            [
                call(request, 40, "qwerty (2)", extra_tags="", fail_silently=False),
            ],
        )
        self.assertEqual(logging.Logger.fatal.call_args_list, [call("qwerty"), call("qwerty")])

    @patch("django.contrib.messages.api.add_message", MagicMock())
    @patch(
        "breathecode.feedback.actions.send_question",
        MagicMock(side_effect=[Exception("qwerty1"), Exception("qwerty2")]),
    )
    @patch("logging.Logger.fatal", MagicMock())
    def test_with_two_users__raises_exceptions__different_exceptions(self):
        request = HttpRequest()
        User = self.bc.database.get_model("auth.User")

        model = self.bc.database.create(user=2)
        db = self.bc.format.to_dict(model.user)

        queryset = User.objects.all()
        result = send_bulk_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("auth.User"), db)

        self.assertEqual(actions.send_question.call_args_list, [call(model.user[0]), call(model.user[1])])
        self.assertEqual(
            api.add_message.call_args_list,
            [
                call(request, 40, "qwerty1 (1) - qwerty2 (1)", extra_tags="", fail_silently=False),
            ],
        )
        self.assertEqual(logging.Logger.fatal.call_args_list, [call("qwerty1"), call("qwerty2")])
