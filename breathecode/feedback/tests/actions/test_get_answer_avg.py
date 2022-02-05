"""
Test /answer
"""
from unittest.mock import patch
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_mailgun_requests_post_mock,
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
)
from ..mixins import FeedbackTestCase
from ...actions import get_student_answer_avg, strings


class AnswerTestSuite(FeedbackTestCase):
    """
    🔽🔽🔽 Without Cohort
    """
    def test_get_answer_avg(self):

        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     profile_academy=True,
                                     answer_status='ANSWERED',
                                     answer_score=8)

        # try:
        average = get_student_answer_avg(model['user'].id, model['answer'].cohort.id)
        # except Exception as e:
        # self.assertEqual(str(e), 'without-cohort-or-cannot-determine-cohort')

        self.assertEqual(average, model['answer'].score)
