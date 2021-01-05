"""
Test /eventbrite/webhook
"""
from datetime import datetime
from unittest.mock import patch
from rest_framework import status
from django.urls.base import reverse_lazy
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_requests_post_mock,
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
)
from ..mixins import EventTestCase
from ...actions import sync_org_venues

class EventbriteWebhookTestSuite(EventTestCase):
    """Test /eventbrite/webhook"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_eventbrite_webhook_without_auth(self):
        """Test /eventbrite/webhook without auth"""
        url = reverse_lazy('events:eventbrite_webhook')
        response = self.client.post(url, self.data(), headers=self.headers(), format='json')
        print(response.__dict__)
        print(response)
        print(response.data)
        # json = response.json()

        # self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_eventbrite_webhook_without_data(self):
        """Test /eventbrite/webhook without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('events:eventbrite_webhook')
        response = self.client.post(url, self.data(), headers=self.headers(), format='json')
        print(response.__dict__)
        print(response)
        print(response.data)
        # json = response.json()

        # self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)