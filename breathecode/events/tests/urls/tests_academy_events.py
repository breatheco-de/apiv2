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

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_all_academy_events_no_cap(self):
    #     self.headers(academy=4)
    #     url = reverse_lazy('events:academy_all_events')
    #     model = self.generate_models(authenticate=True, profile_academy=True,
    #         capability='read_event', role='potato', syllabus=True)

    #     response = self.client.get(url)
    #     json = response.json()
    #     expected = {}

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, 403)

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
        expected = [{
            'banner': model['event'].banner,
            'ending_at': self.datetime_to_iso(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'id': model['event'].id,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'starting_at': self.datetime_to_iso(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'venue': model['event'].venue
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': 1,
            'author_id': 1,
            'banner': model['event'].banner,
            'capacity': model['event'].capacity,
            'description': None,
            'ending_at': model['event'].ending_at,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host_id': 1,
            'id': 1,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_pagination(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base)
            for _ in range(0, 105)]
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'excerpt': model['event'].excerpt,
            'title': model['event'].title,
            'lang': model['event'].lang,
            'url': model['event'].url,
            'banner': model['event'].banner,
            'starting_at': self.datetime_to_iso(model['event'].starting_at),
            'ending_at': self.datetime_to_iso(model['event'].ending_at),
            'status': model['event'].status,
            'event_type': model['event'].event_type,
            'online_event': model['event'].online_event,
            'venue': model['event'].venue
        } for model in models]
        expected.sort(key=lambda x: x['starting_at'], reverse=True)
        expected = expected[0:100]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': model['event'].academy_id,
            'author_id': model['event'].author_id,
            'banner': model['event'].banner,
            'capacity': model['event'].capacity,
            'description': None,
            'ending_at': model['event'].ending_at,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host_id': model['event'].host_id,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_pagination_first_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=0'
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base)
            for _ in range(0, 9)]
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'excerpt': model['event'].excerpt,
            'title': model['event'].title,
            'lang': model['event'].lang,
            'url': model['event'].url,
            'banner': model['event'].banner,
            'starting_at': self.datetime_to_iso(model['event'].starting_at),
            'ending_at': self.datetime_to_iso(model['event'].ending_at),
            'status': model['event'].status,
            'event_type': model['event'].event_type,
            'online_event': model['event'].online_event,
            'venue': model['event'].venue
        } for model in models]
        expected.sort(key=lambda x: x['starting_at'], reverse=True)
        expected = expected[0:5]
        expected = {
            'count': 10,
            'first': None,
            'next': 'http://testserver/v1/events/academy/event?limit=5&offset=5',
            'previous': None,
            'last': 'http://testserver/v1/events/academy/event?limit=5&offset=5',
            'results': expected
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': model['event'].academy_id,
            'author_id': model['event'].author_id,
            'banner': model['event'].banner,
            'capacity': model['event'].capacity,
            'description': None,
            'ending_at': model['event'].ending_at,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host_id': model['event'].host_id,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_pagination_last_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=5'
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base)
            for _ in range(0, 9)]
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'excerpt': model['event'].excerpt,
            'title': model['event'].title,
            'lang': model['event'].lang,
            'url': model['event'].url,
            'banner': model['event'].banner,
            'starting_at': self.datetime_to_iso(model['event'].starting_at),
            'ending_at': self.datetime_to_iso(model['event'].ending_at),
            'status': model['event'].status,
            'event_type': model['event'].event_type,
            'online_event': model['event'].online_event,
            'venue': model['event'].venue
        } for model in models]
        expected.sort(key=lambda x: x['starting_at'], reverse=True)
        expected = expected[5:10]
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/events/academy/event?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/events/academy/event?limit=5',
            'last': None,
            'results': expected
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': model['event'].academy_id,
            'author_id': model['event'].author_id,
            'banner': model['event'].banner,
            'capacity': model['event'].capacity,
            'description': None,
            'ending_at': model['event'].ending_at,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host_id': model['event'].host_id,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_all_academy_events_pagination_after_last_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=10'
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_event', role='potato', syllabus=True, event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base)
            for _ in range(0, 9)]
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/events/academy/event?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/events/academy/event?limit=5&offset=5',
            'last': None,
            'results': []
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': model['event'].academy_id,
            'author_id': model['event'].author_id,
            'banner': model['event'].banner,
            'capacity': model['event'].capacity,
            'description': None,
            'ending_at': model['event'].ending_at,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host_id': model['event'].host_id,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None
        } for model in models])
