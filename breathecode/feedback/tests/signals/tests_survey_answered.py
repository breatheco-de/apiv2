"""
Test /academy/survey
"""
import re, urllib
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase


class SurveyAnsweredTestSuite(FeedbackTestCase):
    """Test /academy/survey"""

    @patch('breathecode.feedback.tasks.process_answer_received.delay', MagicMock())
    def test_survey_answered_signal_pending(self):

        from breathecode.feedback.tasks import process_answer_received

        model = self.generate_models(answer=True)
        answer_db = self.model_to_dict(model, 'answer')

        self.assertEqual(process_answer_received.delay.call_args_list, [])
        self.assertEqual(self.all_answer_dict(), [answer_db])

    @patch('breathecode.feedback.tasks.process_answer_received.delay', MagicMock())
    def test_survey_answered_signal_answered(self):

        from breathecode.feedback.tasks import process_answer_received

        answer = {'status': 'ANSWERED'}
        model = self.generate_models(answer=answer)
        answer_db = self.model_to_dict(model, 'answer')

        self.assertEqual(process_answer_received.delay.call_args_list, [call(1)])
        self.assertEqual(self.all_answer_dict(), [answer_db])
