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
from datetime import datetime
from django.utils import timezone

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

    
    def test_all_academy_events_wrong_city(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, 
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?city=patata"
        
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        
    def test_all_academy_events_correct_city(self):
        self.headers(academy=1)
        venue_kwargs = {"city": "santiago"}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, venue_kwargs=venue_kwargs,
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?city=santiago"
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
                'venue': {'city': model['event'].venue.city,
                            'id': model['event'].id,
                            'state': model['event'].venue.state,
                            'street_address': model['event'].venue.street_address,
                            'title': model['event'].venue.title,
                            'zip_code': model['event'].venue.zip_code}}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_wrong_country(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, 
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?country=patata"
        
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_correct_country(self):
        self.headers(academy=1)
        venue_kwargs = {"country": "chile"}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, venue_kwargs=venue_kwargs,
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?country=chile"
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
                'venue': {'city': model['event'].venue.city,
                            'id': model['event'].id,
                            'state': model['event'].venue.state,
                            'street_address': model['event'].venue.street_address,
                            'title': model['event'].venue.title,
                            'zip_code': model['event'].venue.zip_code}}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_wrong_zip_code(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, 
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?zip_code=12345678965412"
        
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_correct_zip_code(self):
        self.headers(academy=1)
        venue_kwargs = {"zip_code": "33178"}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, venue_kwargs=venue_kwargs,
            venue=True, event=True)
        url = reverse_lazy('events:academy_all_events') + "?zip_code=33178"
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
                'venue': {'city': model['event'].venue.city,
                            'id': model['event'].id,
                            'state': model['event'].venue.state,
                            'street_address': model['event'].venue.street_address,
                            'title': model['event'].venue.title,
                            'zip_code': model['event'].venue.zip_code}}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_upcoming(self):
        self.headers(academy=1)
        event_kwargs = {"starting_at": timezone.now()}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, 
            venue=True, event=True, event_kwargs=event_kwargs )
        url = reverse_lazy('events:academy_all_events') + "?past=true"
        
        response = self.client.get(url)
        json = response.json()
        expected =  [{'banner': model['event'].banner,
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
                    'venue': {'city': model['event'].venue.city,
                            'id': model['event'].id,
                            'state': model['event'].venue.state,
                            'street_address': model['event'].venue.street_address,
                            'title': model['event'].venue.title,
                            'zip_code': model['event'].venue.zip_code}}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        

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
       
    
