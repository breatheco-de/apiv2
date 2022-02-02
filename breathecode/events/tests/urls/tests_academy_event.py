import re
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from datetime import datetime
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
from django.utils import timezone


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

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
        expected = {
            'detail': "You (user: 1) don't have this capability: read_event for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    def test_all_academy_events_wrong_city(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?city=patata'

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_correct_city(self):
        self.headers(academy=1)
        venue_kwargs = {'city': 'santiago'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue_kwargs=venue_kwargs,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?city=santiago'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'banner': model['event'].banner,
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'id': model['event'].id,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'host': model['event'].host,
            'venue': {
                'city': model['event'].venue.city,
                'id': model['event'].id,
                'state': model['event'].venue.state,
                'street_address': model['event'].venue.street_address,
                'title': model['event'].venue.title,
                'zip_code': model['event'].venue.zip_code,
                'updated_at': self.bc.datetime.to_iso_string(model.venue.updated_at),
            },
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_wrong_country(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?country=patata'

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_correct_country(self):
        self.headers(academy=1)
        venue_kwargs = {'country': 'chile'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue_kwargs=venue_kwargs,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?country=chile'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'banner': model['event'].banner,
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'id': model['event'].id,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'host': model['event'].host,
            'venue': {
                'city': model['event'].venue.city,
                'id': model['event'].id,
                'state': model['event'].venue.state,
                'street_address': model['event'].venue.street_address,
                'title': model['event'].venue.title,
                'zip_code': model['event'].venue.zip_code,
                'updated_at': self.bc.datetime.to_iso_string(model.venue.updated_at),
            },
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_wrong_zip_code(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?zip_code=12345678965412'

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_correct_zip_code(self):
        self.headers(academy=1)
        venue_kwargs = {'zip_code': '33178'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue_kwargs=venue_kwargs,
                                     venue=True,
                                     event=True)
        url = reverse_lazy('events:academy_all_events') + '?zip_code=33178'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'banner': model['event'].banner,
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'id': model['event'].id,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'host': model['event'].host,
            'venue': {
                'city': model['event'].venue.city,
                'id': model['event'].id,
                'state': model['event'].venue.state,
                'street_address': model['event'].venue.street_address,
                'title': model['event'].venue.title,
                'zip_code': model['event'].venue.zip_code,
                'updated_at': self.bc.datetime.to_iso_string(model.venue.updated_at),
            },
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_upcoming(self):
        self.headers(academy=1)
        event_kwargs = {'starting_at': timezone.now()}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True,
                                     event_kwargs=event_kwargs)
        url = reverse_lazy('events:academy_all_events') + '?past=true'

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'banner': model['event'].banner,
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'id': model['event'].id,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'host': model['event'].host,
            'venue': {
                'city': model['event'].venue.city,
                'id': model['event'].id,
                'state': model['event'].venue.state,
                'street_address': model['event'].venue.street_address,
                'title': model['event'].venue.title,
                'zip_code': model['event'].venue.zip_code,
                'updated_at': self.bc.datetime.to_iso_string(model.venue.updated_at),
            },
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events_not_found(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_all_academy_events(self, models=None):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')

        if models is None:
            models = [
                self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)
            ]

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'banner': model['event'].banner,
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            'event_type': model['event'].event_type,
            'excerpt': model['event'].excerpt,
            'lang': model['event'].lang,
            'online_event': model['event'].online_event,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'status': model['event'].status,
            'title': model['event'].title,
            'url': model['event'].url,
            'venue': model['event'].venue,
            'host': model['event'].host,
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
        } for model in models]

        expected.reverse()

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        } for model in models])
        return models

    def test_all_academy_events__post__without_organization(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        data = {}

        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'organization-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(self.all_event_dict(), [])

    """
    🔽🔽🔽 Post - bad tags
    """

    def test_all_academy_events__post__bad_tags__two_commas(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': ',,',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'two-commas-together', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__with_spaces(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': ' expecto-patronum sirius-black ',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'spaces-are-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__starts_with_comma(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': ',expecto-patronum',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'starts-with-comma', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__ends_with_comma(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': 'expecto-patronum,',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'ends-with-comma', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__one_tag_not_exists(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': 'expecto-patronum',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'tag-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__one_of_two_tags_not_exists(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     tag=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': f'expecto-patronum,{model.tag.slug}',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'tag-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    """
    🔽🔽🔽 Post
    """

    def test_all_academy_events__post__tags_is_blank(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': '',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])

        del json['created_at']
        del json['updated_at']

        expected = {
            'academy': 1,
            'author': None,
            'description': None,
            'event_type': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'tags': '',
            'slug': None,
            'excerpt': None,
            'host': None,
            'id': 1,
            'slug': None,
            'lang': None,
            'online_event': False,
            'organization': 1,
            'published_at': None,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'venue': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': 1,
            'author_id': None,
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'description': None,
            'ending_at': current_date,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'tags': '',
            'slug': None,
            'host': None,
            'id': 1,
            'lang': None,
            'online_event': False,
            'organization_id': 1,
            'published_at': None,
            'starting_at': current_date,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': 'https://www.google.com/',
            'venue_id': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
        }])

    def test_all_academy_events__post__with_tags(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     active_campaign_academy=True,
                                     tag={'tag_type': 'DISCOVERY'},
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'tags': model.tag.slug,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        del json['updated_at']
        del json['created_at']

        expected = {
            'academy': 1,
            'author': None,
            'description': None,
            'event_type': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'slug': None,
            'excerpt': None,
            'host': None,
            'id': 1,
            'lang': None,
            'online_event': False,
            'organization': 1,
            'published_at': None,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'venue': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            'academy_id': 1,
            'author_id': None,
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'description': None,
            'ending_at': current_date,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'tags': data['tags'],
            'slug': None,
            'host': None,
            'id': 1,
            'lang': None,
            'online_event': False,
            'organization_id': 1,
            'published_at': None,
            'starting_at': current_date,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': 'https://www.google.com/',
            'venue_id': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
        }])

    """
    🔽🔽🔽 Pagination
    """

    def test_all_academy_events_pagination(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base) for _ in range(0, 105)]
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
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
            'venue': model['event'].venue,
            'host': model['event'].host,
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
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
            'host': model['event'].host,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
        } for model in models])

    def test_all_academy_events_pagination_first_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=0'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base) for _ in range(0, 9)]
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
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'online_event': model['event'].online_event,
            'venue': model['event'].venue,
            'host': model['event'].host,
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
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
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'host': model['event'].host,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
        } for model in models])

    def test_all_academy_events_pagination_last_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=5'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base) for _ in range(0, 9)]
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['event'].id,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
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
            'venue': model['event'].venue,
            'host': model['event'].host,
            'sync_with_eventbrite': model['event'].sync_with_eventbrite,
            'eventbrite_sync_description': model['event'].eventbrite_sync_description,
            'eventbrite_sync_status': model['event'].eventbrite_sync_status,
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
        self.assertEqual(self.all_event_dict(), [self.bc.format.to_dict(model.event) for model in models])

    def test_all_academy_events_pagination_after_last_five(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_all_events') + '?limit=5&offset=10'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        base = model.copy()
        del base['event']

        models = [model] + [self.generate_models(event=True, models=base) for _ in range(0, 9)]
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
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'host': model['event'].host,
            'id': model['event'].id,
            'lang': None,
            'online_event': False,
            'organization_id': None,
            'published_at': None,
            'starting_at': model['event'].starting_at,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': model['event'].url,
            'venue_id': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
        } for model in models])

    def test_all_academy_events_with_data_testing_cache(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Event__academy_id=1&event_id=None&city=None&'
            'country=None&zip_code=None&upcoming=None&past=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_models = self.test_all_academy_events()
        self.assertEqual(self.cache.keys(), cache_keys)

        self.test_all_academy_events(old_models)
        self.assertEqual(self.cache.keys(), cache_keys)

    def test_academy_event_type_no_results(self):
        self.headers(academy=1)
        url = reverse_lazy('events:type')
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_cohort_with_data_testing_cache_and_remove_in_post(self):
        """Test /cohort without auth"""
        cache_keys = [
            'Event__academy_id=1&event_id=None&city=None&'
            'country=None&zip_code=None&upcoming=None&past=None&limit=None&offset=None'
        ]

        self.assertEqual(self.cache.keys(), [])

        old_model = self.test_all_academy_events()
        self.assertEqual(self.cache.keys(), cache_keys)

        self.headers(academy=1)

        base = old_model[0].copy()

        del base['profile_academy']
        del base['capability']
        del base['role']
        del base['user']

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     models=base)

        url = reverse_lazy('events:academy_all_events')
        current_date = self.datetime_now()
        data = {
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])

        del json['created_at']
        del json['updated_at']

        expected = {
            'academy': 1,
            'author': None,
            'description': None,
            'event_type': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host': None,
            'id': 2,
            'lang': None,
            'online_event': False,
            'organization': 1,
            'published_at': None,
            'status': 'DRAFT',
            'tags': '',
            'slug': None,
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'venue': None,
            'sync_with_eventbrite': False,
            'currency': 'USD',
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(old_model[0], 'event'),
        }, {
            'academy_id': 1,
            'author_id': None,
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'description': None,
            'ending_at': current_date,
            'event_type_id': None,
            'eventbrite_id': None,
            'eventbrite_organizer_id': None,
            'eventbrite_status': None,
            'eventbrite_url': None,
            'excerpt': None,
            'host': None,
            'id': 2,
            'lang': None,
            'online_event': False,
            'organization_id': 1,
            'published_at': None,
            'starting_at': current_date,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'url': 'https://www.google.com/',
            'venue_id': None,
            'sync_with_eventbrite': False,
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'currency': 'USD',
        }])
        self.assertEqual(self.cache.keys(), [])

        base = [
            self.generate_models(authenticate=True, models=old_model[0]),
            self.generate_models(event=self.get_event(2), models=base),
        ]

        self.test_all_academy_events(base)
        self.assertEqual(self.cache.keys(), cache_keys)

    def test_academy_event_type_with_results(self):
        self.headers(academy=1)
        # TODO: this is bad placed
        url = reverse_lazy('events:type')
        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs)

        response = self.client.get(url)
        json = response.json()
        expected = [{
            'academy': model['event_type'].academy,
            'id': model['event_type'].id,
            'name': model['event_type'].name,
            'slug': model['event_type'].slug,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])

    def test_academy_event_type_no_match_slug(self):
        self.headers(academy=1)
        url = reverse_lazy('events:type') + '?academy=banana'
        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])
