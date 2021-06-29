"""
Test /answer/:id/tracker.png
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase


class AnswerIdTrackerTestSuite(FeedbackTestCase):
    """Test /answer/:id/tracker.png"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_tracker_without_auth(self):
        """Test /answer/:id/tracker.png without auth"""
        url = reverse_lazy('feedback:answer_id_tracker',
                           kwargs={'answer_id': 9999})
        response = self.client.get(url)

        self.assertEqual(response['content-type'], 'image/png')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_tracker_without_data(self):
        """Test /answer/:id/tracker.png without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('feedback:answer_id_tracker',
                           kwargs={'answer_id': 9999})
        response = self.client.get(url)

        self.assertEqual(response['content-type'], 'image/png')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_tracker_with_data_without_status(self):
        """Test /answer/:id/tracker.png without auth"""
        model = self.generate_models(authenticate=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id_tracker',
                           kwargs={'answer_id': model['answer'].id})
        response = self.client.get(url)

        # db['status'] = 'OPENED'

        self.assertEqual(response['content-type'], 'image/png')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_tracker_with_data(self):
        """Test /answer/:id/tracker.png without auth"""
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id_tracker',
                           kwargs={'answer_id': model['answer'].id})
        response = self.client.get(url)

        db['status'] = 'OPENED'

        self.assertEqual(response['content-type'], 'image/png')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.check_all_opened_at_and_remove_it(self.all_answer_dict()),
            [db])
