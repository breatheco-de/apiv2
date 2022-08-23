from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from django.utils import timezone


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_all_academy_events_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event')
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
        url = reverse_lazy('events:academy_event') + '?city=patata'

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
        url = reverse_lazy('events:academy_event') + '?city=santiago'
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
        url = reverse_lazy('events:academy_event') + '?country=patata'

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
        url = reverse_lazy('events:academy_event') + '?country=chile'
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
        url = reverse_lazy('events:academy_event') + '?zip_code=12345678965412'

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
        url = reverse_lazy('events:academy_event') + '?zip_code=33178'
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
        url = reverse_lazy('events:academy_event') + '?past=true'

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
        url = reverse_lazy('events:academy_event')
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

    def test_all_academy_events(self):
        self.check_all_academy_events()

    def test_all_academy_events__post__without_organization(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_event')
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

        url = reverse_lazy('events:academy_event')
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

        url = reverse_lazy('events:academy_event')
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

        url = reverse_lazy('events:academy_event')
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

        url = reverse_lazy('events:academy_event')
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

        url = reverse_lazy('events:academy_event')
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

        expected = {'detail': 'have-less-two-tags', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    def test_all_academy_events__post__bad_tags__two_tags_not_exists(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': 'expecto-patronum,wingardium-leviosa',
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

        url = reverse_lazy('events:academy_event')
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
    🔽🔽🔽 Post bad slug
    """

    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_all_academy_events__post__bad_slug(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     active_campaign_academy=True,
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'they-killed-kenny',
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
            'slug': 'they-killed-kenny',
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
            'tags': ','.join([x.slug for x in model.tag]),
        }])

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

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': '',
            'slug': 'event-they-killed-kenny',
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data)
        json = response.json()

        expected = {'detail': 'empty-tags', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [])

    @patch('breathecode.events.signals.event_saved.send', MagicMock())
    def test_all_academy_events__post__event_exist_with_the_same_eventbrite_id_as_null(self):
        self.headers(academy=1)

        event = {'eventbrite_id': None}
        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     event=event,
                                     capability='crud_event',
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     active_campaign_academy=True,
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'EVENT-THEY-KILLED-KENNY',
            'url': 'https://www.google.com/',
            'eventbrite_id': None,
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.post(url, data, format='json')
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
            'id': 2,
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
            'slug': 'event-they-killed-kenny',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            **self.bc.format.to_dict(model.event),
            'eventbrite_id': None,
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
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'event-they-killed-kenny',
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
            'currency': 'USD',
        }])

    def test_all_academy_events__post__tags_is_blank__slug_in_uppercase(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     active_campaign_academy=True,
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'EVENT-THEY-KILLED-KENNY',
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
            'slug': 'event-they-killed-kenny',
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
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'event-they-killed-kenny',
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

    def test_all_academy_events__post__with_tags__without_acp(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': ','.join([x.slug for x in model.tag]),
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

    def test_all_academy_events__post__with_tags(self):
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     active_campaign_academy=True,
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': ','.join([x.slug for x in model.tag]),
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
    🔽🔽🔽 Put with duplicate tags
    """

    def test_all_academy_events__post__with_duplicate_tags(self):
        self.headers(academy=1)

        tags = [
            {
                'slug': 'they-killed-kenny',
                'tag_type': 'DISCOVERY'
            },
            {
                'slug': 'they-killed-kenny',
                'tag_type': 'DISCOVERY'
            },
            {
                'slug': 'kenny-has-born-again',
                'tag_type': 'DISCOVERY'
            },
        ]
        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     active_campaign_academy=True,
                                     tag=tags,
                                     capability='crud_event',
                                     role='potato')

        url = reverse_lazy('events:academy_event')
        current_date = self.datetime_now()
        data = {
            'tags': 'they-killed-kenny,kenny-has-born-again',
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

    def test_academy_event_type_no_results(self):
        self.headers(academy=1)
        # TODO: this is bad placed
        url = reverse_lazy('events:type')
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

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

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_all_academy_events__spy_extensions(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True)

        url = reverse_lazy('events:academy_event') + '?city=patata'
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'PaginationExtension', 'SortExtension']),
        ])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_all_academy_events__spy_extension_arguments(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     venue=True,
                                     event=True)

        url = reverse_lazy('events:academy_event') + '?city=patata'
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=EventCache, sort='-starting_at', paginate=True),
        ])

    """
    🔽🔽🔽 DELETE
    """

    def test_academy_event__delete__without_lookups(self):
        status = 'DRAFT'
        self.headers(academy=1)

        event = {'status': status}
        model = self.generate_models(authenticate=True,
                                     role=1,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=(2, event))

        url = reverse_lazy('events:academy_event')

        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'without-lookups-and-event-id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of('events.Event'), self.bc.format.to_dict(model.event))

    def test_academy_event__delete__can_delete(self):
        status = 'DRAFT'
        self.headers(academy=1)

        event = {'status': status}
        model = self.generate_models(authenticate=True,
                                     role=1,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=(2, event))

        url = reverse_lazy('events:academy_event') + f'?id={",".join([str(x.id) for x in model.event])}'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.bc.database.list_of('events.Event'), [])

    def test_academy_event__delete__bad_status(self):
        statuses = ['ACTIVE', 'DELETED']
        for status in statuses:

            event = {'status': status}
            model = self.generate_models(user=1,
                                         role=1,
                                         capability='crud_event',
                                         profile_academy=1,
                                         event=(2, event))

            self.bc.request.set_headers(academy=model.academy.id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('events:academy_event') + f'?id={",".join([str(x.id) for x in model.event])}'

            response = self.client.delete(url)
            json = response.json()
            expected = {
                'failure': [{
                    'detail':
                    'non-draft-event',
                    'resources': [{
                        'display_field': 'slug',
                        'display_value': model.event[0].slug,
                        'pk': model.event[0].id,
                    }, {
                        'display_field': 'slug',
                        'display_value': model.event[1].slug,
                        'pk': model.event[1].id,
                    }],
                    'status_code':
                    400,
                }],
                'success': []
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 207)
            self.assertEqual(self.bc.database.list_of('events.Event'), self.bc.format.to_dict(model.event))

            self.bc.database.delete('events.Event')

    def test_academy_event__delete__all_errors_and_success_cases(self):
        bad_statuses = ['ACTIVE', 'DELETED']

        events_with_bad_statuses = [{
            'status': status,
            'slug': self.bc.fake.slug(),
        } for status in bad_statuses]
        events_from_other_academy = [{
            'status': 'DRAFT',
            'academy_id': 2,
            'slug': None,
        }, {
            'status': 'DRAFT',
            'academy_id': 2,
            'slug': None,
        }]
        right_events = [{
            'status': 'DRAFT',
            'academy_id': 1,
            'slug': self.bc.fake.slug(),
        }, {
            'status': 'DRAFT',
            'academy_id': 1,
            'slug': self.bc.fake.slug(),
        }]
        events = events_with_bad_statuses + events_from_other_academy + right_events
        model = self.generate_models(user=1,
                                     role=1,
                                     academy=2,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=events)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('events:academy_event') + f'?id={",".join([str(x.id) for x in model.event])}'

        response = self.client.delete(url)
        json = response.json()
        expected = {
            'success': [{
                'status_code':
                204,
                'resources': [{
                    'pk': model.event[4].id,
                    'display_field': 'slug',
                    'display_value': model.event[4].slug,
                }, {
                    'pk': model.event[5].id,
                    'display_field': 'slug',
                    'display_value': model.event[5].slug,
                }],
            }],
            'failure': [{
                'detail':
                'not-found',
                'status_code':
                400,
                'resources': [{
                    'pk': model.event[2].id,
                    'display_field': 'slug',
                    'display_value': model.event[2].slug,
                }, {
                    'pk': model.event[3].id,
                    'display_field': 'slug',
                    'display_value': model.event[3].slug,
                }],
            }, {
                'detail':
                'non-draft-event',
                'status_code':
                400,
                'resources': [{
                    'pk': model.event[0].id,
                    'display_field': 'slug',
                    'display_value': model.event[0].slug,
                }, {
                    'pk': model.event[1].id,
                    'display_field': 'slug',
                    'display_value': model.event[1].slug,
                }],
            }]
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 207)
        self.assertEqual(self.bc.database.list_of('events.Event'), self.bc.format.to_dict(model.event[:4]))
