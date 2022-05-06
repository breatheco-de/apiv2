"""
Test /answer
"""
from unittest.mock import patch
# from breathecode.tests.mocks import (
#     GOOGLE_CLOUD_PATH,
#     apply_google_cloud_client_mock,
#     apply_google_cloud_bucket_mock,
#     apply_google_cloud_blob_mock,
#     MAILGUN_PATH,
#     MAILGUN_INSTANCES,
#     apply_mailgun_requests_post_mock,
#     SLACK_PATH,
#     SLACK_INSTANCES,
#     apply_slack_requests_request_mock,
# )
from ..mixins import FeedbackTestCase
from ...actions import send_survey_group
from breathecode.utils import ValidationException


class AnswerTestSuite(FeedbackTestCase):
    def test_send_survey_group(self):

        with self.assertRaisesMessage(ValidationException, 'missing-survey-or-cohort'):

            send_survey_group()

    def test_when_survey_and_cohort_do_not_match(self):

        model = self.generate_models(cohort=2, survey=1)

        with self.assertRaisesMessage(ValidationException, 'survey-does-not-match-cohort'):

            send_survey_group(model.survey, model.cohort[1])

    def test_when_cohort_does_not_have_teacher_assigned_to_survey(self):
        wrong_roles = ['ASSISTANT', 'REVIEWER', 'STUDENT']

        for role in wrong_roles:

            model = self.generate_models(cohort=1, survey=1, cohort_user={'role': role})

            with self.assertRaisesMessage(ValidationException, 'cohort-must-have-teacher-assigned-to-survey'):

                send_survey_group(model.survey, model.cohort)

    def test_when_educational_status_is_active_or_graduated(self):

        statuses = ['ACTIVE', 'GRADUATED']

        for status in statuses:
            cohort_user = [{'role': 'TEACHER'}, {'role': 'STUDENT', 'educational_status': status}]

            model = self.generate_models(cohort=1, survey=1, cohort_user=cohort_user)

            # with self.assertRaisesMessage(ValidationException, 'cohort-must-have-teacher-assigned-to-survey'):

            result = send_survey_group(model.survey, model.cohort)

            expected = {'success': [f'Survey scheduled to send for {model.user.email}'], 'error': []}

            self.assertEqual(result, expected)

    def test_when_educational_status_is_all_of_the_others(self):

        statuses = ['POSTPONED', 'SUSPENDED', 'DROPPED']

        for status in statuses:

            self.bc.database.delete('feedback.Survey')
            cohort_user = [{'role': 'TEACHER'}, {'role': 'STUDENT', 'educational_status': status}]

            model = self.generate_models(cohort=1, survey=1, cohort_user=cohort_user)

            result = send_survey_group(model.survey, model.cohort)

            expected = {
                'success': [],
                'error':
                [f"Survey NOT sent to {model.user.email} because it's not an active or graduated student"]
            }

            self.assertEqual(result, expected)

            self.assertEqual(self.bc.database.list_of('feedback.Survey'),
                             [self.bc.format.to_dict(model.survey)])
