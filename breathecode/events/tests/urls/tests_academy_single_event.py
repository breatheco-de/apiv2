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

    def test_academy_single_event_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={"event_id":1})
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={"event_id":1})
        self.generate_models(authenticate=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 1) don't have this capability: read_event for academy 1", 'status_code': 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_single_event_without_data(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={"event_id":1})
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True)
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Event not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_single_event_with_data(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={"event_id":1})
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event= True)
        
        response = self.client.get(url)
        json = response.json()
        print('json:', json)
        expected = {
                    'id': model['event'].id,
                    'excerpt': model['event'].excerpt,
                    'title': model['event'].title,
                    'lang': model['event'].lang,
                    'url': model['event'].url,
                    'banner': model['event'].banner,
                    'starting_at': datetime_to_iso_format(model['event'].starting_at),
                    'ending_at': datetime_to_iso_format(model['event'].ending_at),
                    'status': model['event'].status,
                    'event_type': model['event'].event_type,
                    'online_event': model['event'].online_event,
                    'venue': model['event'].venue, 
                    'academy':{'id': 1, 
                    'slug': model['academy'].slug, 
                    'name': model['academy'].name, 
                    'city': {'name': model['event'].academy.city.name}}}
                    
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    