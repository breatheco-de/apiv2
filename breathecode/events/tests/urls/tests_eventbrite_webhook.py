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
    EVENTBRITE_PATH,
    EVENTBRITE_INSTANCES,
    apply_eventbrite_requests_post_mock,
    EVENTBRITE_ORDER_URL,
)
from ..mixins import EventTestCase
from ...actions import sync_org_venues

class EventbriteWebhookTestSuite(EventTestCase):
    """Test /eventbrite/webhook"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    def test_eventbrite_webhook_without_data(self):
        """Test /eventbrite/webhook without auth"""
        # self.generate_models(authenticate=True)
        url = reverse_lazy('events:eventbrite_webhook')
        response = self.client.post(url, {}, headers=self.headers(), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    def test_eventbrite_webhook_without_data2(self):
        """Test /eventbrite/webhook without auth"""
        # self.generate_models(authenticate=True)
        url = reverse_lazy('events:eventbrite_webhook')
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        assert False
