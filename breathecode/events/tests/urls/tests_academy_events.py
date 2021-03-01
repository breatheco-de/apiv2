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

class AcademyEventsTestSuite(EventTestCase):
    def test_all_academy_events_no_auth(self):
        self.headers(academy=1)
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
    def test_all_academy_events_without_data(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_with_data(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = [{'banner': model['event'].banner,
                    'ending_at': datetime_to_iso_format(model['event'].ending_at),
                    'event_type': model['event'].event_type,
                    'excerpt': model['event'].excerpt,
                    'id': model['event'].id,
                    'lang': model['event'].lang,
                    'online_event': model['event'].online_event,
                    'starting_at': datetime_to_iso_format(model['event'].starting_at),
                    'status': model['event'].status,
                    'title': model['event'].title,
                    'url': model['event'].url,
                    'venue': model['event'].venue}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
       
    # no funciona
    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_all_academy_single_event_ok(self):
    #     self.headers(academy=1)
    #     url = reverse_lazy('events:academy_single_event', kwargs={"event_id":1})
    #     model = self.generate_models(authenticate=True, profile_academy=True,
    #         capability='read_event', role='potato', syllabus=True)
        
    #     response = self.client.get(url)
    #     json = response.json()
    #     expected = []

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, 200)
    #     assert False

        # funciona pasandole event id true
