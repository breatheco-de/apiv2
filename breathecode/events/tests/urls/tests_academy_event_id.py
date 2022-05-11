from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from unittest.mock import MagicMock, call, patch


class AcademyEventIdTestSuite(EventTestCase):
    cache = EventCache()

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_event_id_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_all_academy_events_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_event for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_event_id_invalid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_event_id_valid_id(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id_put__without_organization(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        data = {}

        response = self.client.put(url, data)
        json = response.json()
        expected = {'detail': 'organization-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id_put_without_required_fields(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
        }

        response = self.client.put(url, data)
        json = response.json()

        expected = {
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__two_commas(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__with_spaces(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__starts_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__ends_with_comma(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__one_tag_not_exists(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

        expected = {'detail': 'have-less-two-tags', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [self.model_to_dict(model, 'event')])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__two_tags_not_exists(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': 'expecto-patronum,wingardium-leviosa',
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

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
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

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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
    🔽🔽🔽 Put
    """

    def test_academy_cohort_id__put(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     active_campaign_academy=True,
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ','.join([x.slug for x in model.tag]),
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
            'tags': '',
            'slug': None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            **data,
            'organization_id': 1,
            'starting_at': current_date,
            'ending_at': current_date,
            'slug': None,
        }])

    """
    🔽🔽🔽 Put, tags empty
    """

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__tags_is_blank(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
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

        expected = {'detail': 'empty-tags', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    """
    🔽🔽🔽 Try to update the slug
    """

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__tags_is_blank__try_to_update_the_slug(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     capability='crud_event',
                                     role='potato2',
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     active_campaign_academy=True,
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ','.join([x.slug for x in model.tag]),
            'slug': 'EVENT-THEY-KILLED-KENNY',
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'try-update-slug', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__with_tags__without_acp(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     organization=True,
                                     profile_academy=True,
                                     academy=True,
                                     tag=(2, {
                                         'tag_type': 'DISCOVERY'
                                     }),
                                     capability='crud_event',
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ','.join([x.slug for x in model.tag]),
            'capacity': 11,
            'starting_at': self.datetime_to_iso(current_date),
            'ending_at': self.datetime_to_iso(current_date),
        }

        response = self.client.put(url, data, format='json')
        json = response.json()

        expected = {'detail': 'tag-not-exist', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
        }])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__with_tags(self):
        """Test /cohort without auth"""
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
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': ','.join([x.slug for x in model.tag]),
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            **data,
            'organization_id': 1,
            'starting_at': current_date,
            'ending_at': current_date,
        }])

    """
    🔽🔽🔽 Put with duplicate tags
    """

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    def test_academy_cohort_id__put__with_duplicate_tags(self):
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
                                     role='potato2',
                                     event=True)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        current_date = self.datetime_now()
        data = {
            'id': 1,
            'url': 'https://www.google.com/',
            'banner': 'https://www.google.com/banner',
            'tags': 'they-killed-kenny,kenny-has-born-again',
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_dict(), [{
            **self.model_to_dict(model, 'event'),
            **data,
            'organization_id': 1,
            'starting_at': current_date,
            'ending_at': current_date,
        }])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_academy_event_id__spy_extensions(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'PaginationExtension', 'SortExtension']),
        ])

    @patch('breathecode.marketing.signals.downloadable_saved.send', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_academy_event_id__spy_extension_arguments(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_event',
                                     role='potato',
                                     syllabus=True,
                                     event=True)

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=EventCache, sort='-starting_at', paginate=True),
        ])

    """
    🔽🔽🔽 DELETE
    """

    def test_academy_event__delete__with_lookups(self):
        status = 'DRAFT'
        self.headers(academy=1)

        event = {'status': status}
        model = self.generate_models(authenticate=True,
                                     role=1,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=(2, event))

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1}) + '?id=1,2'

        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'lookups-and-event-id-together', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of('events.Event'), self.bc.format.to_dict(model.event))

    def test_academy_event__delete__deleting(self):
        status = 'DRAFT'
        self.headers(academy=1)

        event = {'status': status}
        model = self.generate_models(authenticate=True,
                                     role=1,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=event)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.bc.database.list_of('events.Event'), [])

    def test_academy_event__delete__non_draft_event(self):
        statuses = ['ACTIVE', 'DELETED']
        for status in statuses:

            event = {'status': status}
            model = self.generate_models(authenticate=True,
                                         role=1,
                                         capability='crud_event',
                                         profile_academy=1,
                                         event=event)

            url = reverse_lazy('events:academy_event_id', kwargs={'event_id': model.event.id})

            self.headers(academy=model.academy.id)
            response = self.client.delete(url)
            json = response.json()
            expected = {'detail': 'non-draft-event', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.bc.database.list_of('events.Event'), [self.bc.format.to_dict(model.event)])
            self.bc.database.delete('events.Event')

    def test_academy_event__delete__deleting_from_other_academy(self):
        status = 'DRAFT'
        self.headers(academy=1)

        event = {'status': status, 'academy_id': 2}
        model = self.generate_models(authenticate=True,
                                     role=1,
                                     academy=2,
                                     capability='crud_event',
                                     profile_academy=1,
                                     event=event)

        url = reverse_lazy('events:academy_event_id', kwargs={'event_id': 1})

        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.bc.database.list_of('events.Event'), [self.bc.format.to_dict(model.event)])
