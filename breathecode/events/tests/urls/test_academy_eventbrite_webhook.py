import re
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from datetime import datetime
from breathecode.utils import Cache
from unittest.mock import patch
from ..mixins.new_events_tests_case import EventTestCase


class AcademyEventbriteWebhookTestSuite(EventTestCase):
    def test_all_eventbrite_webhooks(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=1,
                                     capability='read_organization',
                                     role='potato',
                                     cohort=True)
        self.bc.request.authenticate(model.user)
        url = reverse_lazy('events:academy_organizarion_eventbrite_webhook')
        # model = self.generate_models(authenticate=True)
        model = self.bc.database.create(eventbrite_webhook=1)
        response = self.client.get(url)
        json = response.json()
        print(json)
        expected = [{
            'api_url': model['eventbrite_webhook'].api_url,
            'user_id': model['eventbrite_webhook'].user_id,
            'action': model['eventbrite_webhook'].action,
            'webhook_id': model['eventbrite_webhook'].webhook_id,
            'organization_id': model['eventbrite_webhook'].organization_id,
            'endpoint_url': model['eventbrite_webhook'].endpoint_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
