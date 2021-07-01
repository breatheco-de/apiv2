from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from breathecode.utils import Cache
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
from .tests_academy_event import AcademyEventTestSuite


class AcademyEventsTestSuite(EventTestCase):
    cache = EventCache()

    def test_academy_single_event_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event',
                           kwargs={"event_id": 1})

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': 401
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event',
                           kwargs={"event_id": 1})
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail':
            "You (user: 1) don't have this capability: read_event for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_single_event_invalid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event',
                           kwargs={"event_id": 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True)

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Event not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_single_event_valid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event',
                           kwargs={"event_id": 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['event'].id,
            'capacity': model['event'].capacity,
            'description': model['event'].description,
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
            'academy': {
                'id': 1,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
                'city': {
                    'name': model['event'].academy.city.name
                }
            }
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_id_put_without_required_fields(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event',
                           kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
        }

        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'url': ['This field is required.'],
            'banner': ['This field is required.'],
            'capacity': ['This field is required.'],
            'starting_at': ['This field is required.'],
            'ending_at': ['This field is required.']
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_id_put(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event',
                           kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])

        del json['created_at']
        del json['updated_at']

        expected = {
            'academy': 1,
            'author': 1,
            'description': None,
            'event_type': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host': 1,
            'id': 2,
            'lang': None,
            'online_event': False,
            'organization': None,
            'published_at': None,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'venue': None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(),
                         [{
                             **self.model_to_dict(model, 'event'),
                             **data,
                             'starting_at': current_date,
                             'ending_at': current_date,
                         }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_with_data_testing_cache_and_remove_in_put(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Event__academy_id=1&event_id=None&city=None&'
            'country=None&zip_code=None&upcoming=None&past=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_model = AcademyEventTestSuite.test_all_academy_events(self)
        self.assertEqual(self.cache.keys(), cache_keys)

        self.headers(academy=1)

        base = old_model[0].copy()

        del base['profile_academy']
        del base['capability']
        del base['role']
        del base['user']

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     models=base)

        url = reverse_lazy('events:academy_single_event',
                           kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])

        del json['created_at']
        del json['updated_at']

        expected = {
            'academy': 1,
            'author': 1,
            'description': None,
            'event_type': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host': 1,
            'id': 2,
            'lang': None,
            'online_event': False,
            'organization': None,
            'published_at': None,
            'status': 'DRAFT',
            'sync_desc': None,
            'sync_status': 'PENDING',
            'title': None,
            'venue': None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(),
                         [{
                             **self.model_to_dict(model, 'event'),
                             **data,
                             'starting_at': current_date,
                             'ending_at': current_date,
                         }])
        self.assertEqual(self.cache.keys(), [])
        event = old_model[0]['event']

        for x in data:
            setattr(event, x, data[x])

        event.starting_at = current_date
        event.ending_at = current_date
        old_model[0]['event'] = event

        base = [
            self.generate_models(authenticate=True, models=old_model[0]),
        ]

        AcademyEventTestSuite.test_all_academy_events(self, base)
        self.assertEqual(self.cache.keys(), cache_keys)
