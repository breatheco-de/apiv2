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
    OLD_BREATHECODE_PATH,
    apply_old_breathecode_requests_request_mock
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
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, {}, headers=self.headers(), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(self.all_eventbrite_webhook_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    def test_eventbrite_webhook_without_organization(self):
        """Test /eventbrite/webhook without auth"""
        # self.generate_models(authenticate=True)
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(self.all_eventbrite_webhook_dict(), [{
            'action': 'placed',
            'api_url': 'https://www.eventbriteapi.com/v3/events/1/orders/1/',
            'endpoint_url': 'https://something.io/eventbrite/webhook',
            'id': 1,
            'organization_id': '1',
            'status': 'ERROR',
            'status_text': 'Cannot get academy_id or organization doesn\'t exist',
            'user_id': '123456789012',
            'webhook_id': '1234567'
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    def test_eventbrite_webhook_without_event(self):
        """Test /eventbrite/webhook without auth"""
        # self.generate_models(authenticate=True)
        self.generate_models(organization=True)
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_event_checkin_dict(), [])
        self.assertEqual(self.all_eventbrite_webhook_dict(), [{
            'action': 'placed',
            'api_url': 'https://www.eventbriteapi.com/v3/events/1/orders/1/',
            'endpoint_url': 'https://something.io/eventbrite/webhook',
            'id': 1,
            'organization_id': '1',
            'status': 'ERROR',
            'status_text': 'event doesn\'t exist',
            'user_id': '123456789012',
            'webhook_id': '1234567'
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    def test_eventbrite_webhook_without_active_campaign_academy(self):
        """Test /eventbrite/webhook without auth"""
        self.generate_models(organization=True, event=True, eventbrite_event_id=1, attendee=True)
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_eventbrite_webhook_dict(), [{
            'action': 'placed',
            'api_url': 'https://www.eventbriteapi.com/v3/events/1/orders/1/',
            'endpoint_url': 'https://something.io/eventbrite/webhook',
            'id': 1,
            'organization_id': '1',
            'status': 'ERROR',
            'status_text': 'ActiveCampaignAcademy doesn\'t exist',
            'user_id': '123456789012',
            'webhook_id': '1234567'
        }])

        self.assertEqual(self.all_event_checkin_dict(), [{
            'attendee_id': 2,
            'email': 'john.smith@example.com',
            'event_id': 1,
            'id': 1,
            'status': 'PENDING'
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    @patch(OLD_BREATHECODE_PATH['request'], apply_old_breathecode_requests_request_mock())
    def test_eventbrite_webhook_without_automation(self):
        """Test /eventbrite/webhook without auth"""
        self.generate_models(organization=True, event=True, eventbrite_event_id=1, attendee=True,
            active_campaign_academy=True, in_miami=True)
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_eventbrite_webhook_dict(), [{
            'action': 'placed',
            'api_url': 'https://www.eventbriteapi.com/v3/events/1/orders/1/',
            'endpoint_url': 'https://something.io/eventbrite/webhook',
            'id': 1,
            'organization_id': '1',
            'status': 'ERROR',
            'status_text': 'Automation doesn\'t exist',
            'user_id': '123456789012',
            'webhook_id': '1234567'
        }])

        self.assertEqual(self.all_event_checkin_dict(), [{
            'attendee_id': 2,
            'email': 'john.smith@example.com',
            'event_id': 1,
            'id': 1,
            'status': 'PENDING'
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(EVENTBRITE_PATH['get'], apply_eventbrite_requests_post_mock())
    @patch(OLD_BREATHECODE_PATH['request'], apply_old_breathecode_requests_request_mock())
    def test_eventbrite_webhook(self):
        """Test /eventbrite/webhook without auth"""
        self.generate_models(organization=True, event=True, eventbrite_event_id=1, attendee=True,
            active_campaign_academy=True, in_miami=True, automation=True, with_event_attendancy_automation=True)
        url = reverse_lazy('events:eventbrite_webhook_id', kwargs={'organization_id': 1})
        response = self.client.post(url, self.data('placed', EVENTBRITE_ORDER_URL),
            headers=self.headers('placed'), format='json')
        content = response.content

        self.assertEqual(content, b'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_eventbrite_webhook_dict(), [{
            'action': 'placed',
            'api_url': 'https://www.eventbriteapi.com/v3/events/1/orders/1/',
            'endpoint_url': 'https://something.io/eventbrite/webhook',
            'id': 1,
            'organization_id': '1',
            'status': 'DONE',
            'status_text': None,
            'user_id': '123456789012',
            'webhook_id': '1234567'
        }])

        self.assertEqual(self.all_event_checkin_dict(), [{
            'attendee_id': 2,
            'email': 'john.smith@example.com',
            'event_id': 1,
            'id': 1,
            'status': 'PENDING'
        }])
