import re
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from datetime import datetime
from breathecode.utils import Cache
from unittest.mock import patch
from ..mixins.new_events_tests_case import EventTestCase
from django.utils import timezone


class AcademyEventbriteWebhookTestSuite(EventTestCase):
    def test_all_eventbrite_webhooks(self):
        self.headers(academy=1)

        url = reverse_lazy('events:academy_organizarion_eventbrite_webhook')
        eventbrite_webhook = {'organization_id': 1}
        start = timezone.now()
        model = self.bc.database.create(eventbrite_webhook=eventbrite_webhook,
                                        profile_academy=1,
                                        organization=1,
                                        capability='read_organization',
                                        role='potato',
                                        cohort=1)
        end = timezone.now()
        self.bc.request.authenticate(model.user)
        response = self.client.get(url)
        json = response.json()

        created_at = self.bc.datetime.from_iso_string(json[0]['created_at'])
        updated_at = self.bc.datetime.from_iso_string(json[0]['updated_at'])
        self.bc.check.datetime_in_range(start, end, created_at)
        self.bc.check.datetime_in_range(start, end, updated_at)
        del json[0]['created_at']
        del json[0]['updated_at']

        expected = [{
            'id': model['eventbrite_webhook'].id,
            'status': model['eventbrite_webhook'].status,
            'status_text': model['eventbrite_webhook'].status_text,
            'api_url': model['eventbrite_webhook'].api_url,
            'user_id': model['eventbrite_webhook'].user_id,
            'action': model['eventbrite_webhook'].action,
            'webhook_id': model['eventbrite_webhook'].webhook_id,
            'organization_id': model['eventbrite_webhook'].organization_id,
            'endpoint_url': model['eventbrite_webhook'].endpoint_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
