import re
from django.urls.base import reverse_lazy
from rest_framework import status
from unittest.mock import patch
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from breathecode.services import datetime_to_iso_format
from breathecode.tests.mixins.cache_mixin import CacheMixin


class AcademyVenueTestSuite(EventTestCase):

    def test_academy_venues_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_venues')

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_venues_with_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_venues')
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 1) don't have this capability: read_event for academy 1",
                    'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    def test_academy_venues_with_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_venues')
        self.generate_models(authenticate=True, capability='read_event')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 1) don't have this capability: read_event for academy 1",
                    'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
