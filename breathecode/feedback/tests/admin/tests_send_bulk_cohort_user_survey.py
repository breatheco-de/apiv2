"""
Test /answer
"""
import logging
from unittest.mock import MagicMock, call, patch
from django.http.request import HttpRequest
from django.contrib.auth.models import User
from ..mixins import FeedbackTestCase
from ...admin import send_bulk_cohort_user_survey

from ..mixins import FeedbackTestCase
from ... import actions

from django.contrib.messages import api


class SendSurveyTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 With zero CohortUser
    """

    @patch('django.contrib.messages.api.add_message', MagicMock())
    @patch('breathecode.feedback.actions.send_question', MagicMock())
    def test_with_zero_cohort_users(self):
        request = HttpRequest()

        queryset = User.objects.all()
        result = send_bulk_cohort_user_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

        self.assertEqual(api.add_message.call_args_list, [
            call(request, 25, 'Survey was successfully sent', extra_tags='', fail_silently=False),
        ])
        self.assertEqual(actions.send_question.call_args_list, [])

    """
    🔽🔽🔽 With two CohortUser
    """

    @patch('django.contrib.messages.api.add_message', MagicMock())
    @patch('breathecode.feedback.actions.send_question', MagicMock())
    def test_with_two_cohort_users(self):
        request = HttpRequest()
        CohortUser = self.bc.database.get_model('admissions.CohortUser')

        model = self.bc.database.create(cohort_user=2)
        db = self.bc.format.to_dict(model.cohort_user)

        queryset = CohortUser.objects.all()
        result = send_bulk_cohort_user_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), db)

        self.assertEqual(
            str(api.add_message.call_args_list),
            str([
                call(request, 25, 'Survey was successfully sent', extra_tags='', fail_silently=False),
            ]))
        self.assertEqual(actions.send_question.call_args_list, [
            call(model.user, model.cohort),
            call(model.user, model.cohort),
        ])

    """
    🔽🔽🔽 With two CohortUser raise exceptions
    """

    @patch('django.contrib.messages.api.add_message', MagicMock())
    @patch('breathecode.feedback.actions.send_question', MagicMock(side_effect=Exception('qwerty')))
    @patch('logging.Logger.fatal', MagicMock())
    def test_with_two_cohort_users__raises_exceptions__same_exception(self):
        request = HttpRequest()
        CohortUser = self.bc.database.get_model('admissions.CohortUser')

        model = self.bc.database.create(cohort_user=2)
        db = self.bc.format.to_dict(model.cohort_user)

        queryset = CohortUser.objects.all()
        result = send_bulk_cohort_user_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), db)

        self.assertEqual(actions.send_question.call_args_list, [
            call(model.user, model.cohort),
            call(model.user, model.cohort),
        ])
        self.assertEqual(api.add_message.call_args_list, [
            call(request, 40, 'qwerty (2)', extra_tags='', fail_silently=False),
        ])
        self.assertEqual(logging.Logger.fatal.call_args_list, [call('qwerty'), call('qwerty')])

    @patch('django.contrib.messages.api.add_message', MagicMock())
    @patch('breathecode.feedback.actions.send_question',
           MagicMock(side_effect=[Exception('qwerty1'), Exception('qwerty2')]))
    @patch('logging.Logger.fatal', MagicMock())
    def test_with_two_cohort_users__raises_exceptions__different_exceptions(self):
        request = HttpRequest()
        CohortUser = self.bc.database.get_model('admissions.CohortUser')

        model = self.bc.database.create(cohort_user=2)
        db = self.bc.format.to_dict(model.cohort_user)

        queryset = CohortUser.objects.all()
        result = send_bulk_cohort_user_survey(None, request, queryset)

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), db)

        self.assertEqual(actions.send_question.call_args_list, [
            call(model.user, model.cohort),
            call(model.user, model.cohort),
        ])
        self.assertEqual(api.add_message.call_args_list, [
            call(request, 40, 'qwerty1 (1) - qwerty2 (1)', extra_tags='', fail_silently=False),
        ])
        self.assertEqual(logging.Logger.fatal.call_args_list, [call('qwerty1'), call('qwerty2')])
