"""
Test /answer
"""
from datetime import timedelta
from unittest.mock import patch, MagicMock, call
from ..mixins import FeedbackTestCase
from ...actions import send_survey_group
from breathecode.utils import ValidationException
from django.utils import timezone

import breathecode.feedback.tasks as tasks

UTC_NOW = timezone.now()


class AnswerTestSuite(FeedbackTestCase):

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    def test_send_survey_group(self):

        with self.assertRaisesMessage(ValidationException, 'missing-survey-or-cohort'):

            send_survey_group()
        self.assertEqual(tasks.send_cohort_survey.delay.call_args_list, [])

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    def test_when_survey_and_cohort_do_not_match(self):

        model = self.generate_models(cohort=2, survey=1)

        with self.assertRaisesMessage(ValidationException, 'survey-does-not-match-cohort'):

            send_survey_group(model.survey, model.cohort[1])
        self.assertEqual(tasks.send_cohort_survey.delay.call_args_list, [])

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    def test_when_cohort_does_not_have_teacher_assigned_to_survey(self):
        wrong_roles = ['ASSISTANT', 'REVIEWER', 'STUDENT']

        for role in wrong_roles:

            model = self.generate_models(cohort=1, survey=1, cohort_user={'role': role})

            with self.assertRaisesMessage(ValidationException, 'cohort-must-have-teacher-assigned-to-survey'):

                send_survey_group(model.survey, model.cohort)
            self.assertEqual(tasks.send_cohort_survey.delay.call_args_list, [])

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_when_educational_status_is_active_or_graduated(self):

        statuses = ['ACTIVE', 'GRADUATED']

        for status in statuses:
            cohort_user = [{'role': 'TEACHER'}, {'role': 'STUDENT', 'educational_status': status}]

            model = self.generate_models(cohort=1, survey=1, cohort_user=cohort_user)

            survey = self.bc.format.to_dict(model.survey)

            result = send_survey_group(model.survey, model.cohort)

            expected = {'success': [f'Survey scheduled to send for {model.user.email}'], 'error': []}

            self.assertEqual(result, expected)

            self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
                **survey, 'sent_at':
                UTC_NOW,
                'status':
                'SENT',
                'status_json':
                '{'
                f'"success": ["Survey scheduled to send for {model.user.email}"], "error": []'
                '}'
            }])

            self.bc.database.delete('feedback.Survey')
            self.assertEqual(tasks.send_cohort_survey.delay.call_args_list,
                             [call(model.user.id, model.survey.id)])
            tasks.send_cohort_survey.delay.call_args_list = []

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_when_educational_status_is_all_of_the_others_error(self):

        statuses = ['POSTPONED', 'SUSPENDED', 'DROPPED']

        for status in statuses:

            self.bc.database.delete('feedback.Survey')
            cohort_user = [{'role': 'TEACHER'}, {'role': 'STUDENT', 'educational_status': status}]

            model = self.generate_models(cohort=1, survey=1, cohort_user=cohort_user)

            survey = self.bc.format.to_dict(model.survey)

            result = send_survey_group(model.survey, model.cohort)

            expected = {
                'success': [],
                'error':
                [f"Survey NOT sent to {model.user.email} because it's not an active or graduated student"]
            }

            self.assertEqual(result, expected)

            self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
                **survey, 'sent_at':
                UTC_NOW,
                'status':
                'FATAL',
                'status_json':
                '{"success": [], "error": ["Survey NOT sent to '
                f"{model.user.email} because it's not an active or graduated student\"]"
                '}'
            }])
            self.assertEqual(tasks.send_cohort_survey.delay.call_args_list, [])

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_when_some_cases_are_successful_and_some_are_error(self):

        cohort_users = [{
            'role': 'TEACHER'
        }, {
            'role': 'STUDENT',
            'educational_status': 'ACTIVE'
        }, {
            'role': 'STUDENT',
            'educational_status': 'SUSPENDED'
        }]

        model = self.generate_models(cohort=1, survey=1, cohort_user=cohort_users)

        survey = self.bc.format.to_dict(model.survey)

        result = send_survey_group(model.survey, model.cohort)

        expected = {
            'success': [f'Survey scheduled to send for {model.user.email}'],
            'error':
            [f"Survey NOT sent to {model.user.email} because it's not an active or graduated student"]
        }

        self.assertEqual(result, expected)

        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey, 'sent_at':
            UTC_NOW,
            'status':
            'PARTIAL',
            'status_json':
            '{'
            f'"success": ["Survey scheduled to send for {model.user.email}"], "error": ["Survey NOT sent to '
            f'{model.user.email} because it\'s not an active or graduated student"]'
            '}'
        }])

        self.bc.database.delete('feedback.Survey')
        self.assertEqual(tasks.send_cohort_survey.delay.call_args_list,
                         [call(model.user.id, model.survey.id)])
        tasks.send_cohort_survey.delay.call_args_list = []

    @patch('breathecode.feedback.tasks.send_cohort_survey.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_when_survey_is_none(self):

        model = self.generate_models(cohort=1, cohort_user=[{'role': 'TEACHER'}, {'role': 'STUDENT'}])

        result = send_survey_group(cohort=model.cohort)

        expected = {
            'success': [],
            'error':
            [f"Survey NOT sent to {model.user.email} because it's not an active or graduated student"]
        }

        self.assertEqual(result, expected)

        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            'sent_at':
            UTC_NOW,
            'status':
            'FATAL',
            'status_json':
            '{"success": [], "error": ["Survey NOT sent to '
            f"{model.user.email} because it's not an active or graduated student\"]"
            '}',
            'scores':
            None,
            'cohort_id':
            1,
            'duration':
            timedelta(days=1),
            'id':
            1,
            'lang':
            'en',
            'max_assistants_to_ask':
            2,
            'max_teachers_to_ask':
            1,
            'response_rate':
            None,
            'scores':
            None,
        }])
        self.assertEqual(tasks.send_cohort_survey.delay.call_args_list, [])
