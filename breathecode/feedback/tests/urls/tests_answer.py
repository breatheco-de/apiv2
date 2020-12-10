"""
Test /answer
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

class AnswerTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_data(self):
        """Test /answer without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'academy': model['answer'].academy,
            'cohort': model['answer'].cohort,
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': model['answer'].mentor,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': model['answer'].user,
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])
