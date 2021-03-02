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
from breathecode.tests.mixins.cache_mixin import CacheMixin

class AcademyEventsTestSuite(EventTestCase):
    def test_all_academy_events_no_auth(self):
        self.headers(academy=4)
        url = reverse_lazy('events:academy_all_events')
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        self.generate_models(authenticate=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 1) don't have this capability: read_event for academy 1", 'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_no_cap(self):
        self.headers(academy=4)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_student', role='potato', syllabus=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = {}

        self.assertEqual(response.status_code, 403)
