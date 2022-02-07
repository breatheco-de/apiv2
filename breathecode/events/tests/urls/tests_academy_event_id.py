from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from .tests_academy_event import AcademyEventTestSuite


class AcademyEventsTestSuite(EventTestCase):
    cache = EventCache()

    def test_academy_single_event_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_event for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    def test_academy_single_event_invalid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
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

    def test_academy_single_event_valid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
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
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'host': model['event'].host,
            'starting_at': datetime_to_iso_format(model['event'].starting_at),
            'ending_at': datetime_to_iso_format(model['event'].ending_at),
            # 'updated_at': datetime_to_iso_format(model['event'].updated_at),
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
            },
            'sync_with_eventbrite': False,
            'eventbrite_sync_status': 'PENDING',
            'eventbrite_sync_description': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_cohort_id_put__without_organization(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        data = {}

        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'organization-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    def test_academy_cohort_id_put_without_required_fields(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
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

    """
    🔽🔽🔽 Put - bad tags
    """

    def test_academy_cohort_id__put__two_commas(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ',,',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'two-commas-together', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    def test_academy_cohort_id__put__with_spaces(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ' expecto-patronum sirius-black ',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'spaces-are-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    def test_academy_cohort_id__put__starts_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ',expecto-patronum',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'starts-with-comma', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    def test_academy_cohort_id__put__ends_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': 'expecto-patronum,',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'ends-with-comma', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    def test_academy_cohort_id__put__one_tag_not_exists(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': 'expecto-patronum',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'tag-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    def test_academy_cohort_id__put__one_of_two_tags_not_exists(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     tag=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': f'expecto-patronum,{model.tag.slug}',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'tag-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    """
    🔽🔽🔽 Put, bad slug
    """

    def test_academy_cohort_id__put__bad_slug(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'slug': 'they-killed-kenny',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'slug-is-not-startswith-event', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    """
    🔽🔽🔽 Put
    """

    def test_academy_cohort_id__put__tags_is_blank(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': '',
            'slug': 'event-they-killed-kenny',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
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
            'host': model['event'].host,
            'id': 2,
            'lang': None,
            'slug': 'event-they-killed-kenny',
            'online_event': False,
            'organization': 1,
            'published_at': None,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'venue': None,
            'sync_with_eventbrite': False,
            'eventbrite_sync_status': 'PENDING',
            'currency': 'USD',
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            **data,
            'organization_id': 1,
            'starting_at': current_date,
            'ending_at': current_date,
        }])

    def test_academy_cohort_id__put__with_tags(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     tag={'tag_type': 'DISCOVERY'},
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': model.tag.slug,
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        del json['updated_at']
        del json['created_at']

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
            'host': model['event'].host,
            'id': 2,
            'lang': None,
            'slug': None,
            'online_event': False,
            'organization': 1,
            'published_at': None,
            'status': 'DRAFT',
            'eventbrite_sync_description': None,
            'eventbrite_sync_status': 'PENDING',
            'title': None,
            'venue': None,
            'sync_with_eventbrite': False,
            'eventbrite_sync_status': 'PENDING',
            'currency': 'USD',
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            **data,
            'organization_id': 1,
            'starting_at': current_date,
            'ending_at': current_date,
        }])

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
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     models=base)

        url = reverse_lazy('events:academy_single_event', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
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
            'tags': model['event'].tags,
            'slug': model['event'].slug,
            'host': model['event'].host,
            'id': 2,
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
