import re

from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from unittest.mock import MagicMock, call, patch

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase


def get_serializer(self, event, event_type, academy, user, data={}):
    return {
        'academy': academy.id,
        'author': user.id,
        'banner': event.banner,
        'capacity': event.capacity,
        'created_at': self.bc.datetime.to_iso_string(event.created_at),
        'currency': event.currency,
        'description': event.description,
        'ending_at': self.bc.datetime.to_iso_string(event.ending_at),
        'event_type': event_type.id,
        'eventbrite_id': event.eventbrite_id,
        'eventbrite_organizer_id': event.eventbrite_organizer_id,
        'eventbrite_status': event.eventbrite_status,
        'eventbrite_sync_description': event.eventbrite_sync_description,
        'eventbrite_sync_status': event.eventbrite_sync_status,
        'eventbrite_url': event.eventbrite_url,
        'excerpt': event.excerpt,
        'host': event.host,
        'id': event.id,
        'lang': event.lang,
        'online_event': event.online_event,
        'live_stream_url': event.live_stream_url,
        'organization': event.organization,
        'published_at': event.published_at,
        'slug': event.slug,
        'starting_at': self.bc.datetime.to_iso_string(event.starting_at),
        'status': event.status,
        'sync_with_eventbrite': event.sync_with_eventbrite,
        'tags': event.tags,
        'title': event.title,
        'updated_at': self.bc.datetime.to_iso_string(event.updated_at),
        'url': event.url,
        'venue': event.venue,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:me')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_zero_items(self):
        self.headers(academy=1)
        url = reverse_lazy('events:me')

        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_one_item__non_visible(self):
        self.headers(academy=1)
        url = reverse_lazy('events:me')

        model = self.bc.database.create(user=1, event=1, event_type=1)
        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Academy hunter
    """

    def test_one_item__academy_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            'academy_id': 2,
            'cohort_id': None,
            'syllabus_id': None,
        }
        event_type = {
            'academy_id': 1,
            'allow_shared_creation': False,
        }
        cohort = {
            'academy_id': 2,
        }
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        model = self.bc.database.create(user=1,
                                        event=2,
                                        event_type=event_type,
                                        academy=2,
                                        cohort=cohort,
                                        cohort_user=1,
                                        event_type_visibility_setting=event_type_visibility_setting)
        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_one_item__academy_visible(self):
        cases = [
            (
                {
                    'academy_id': 1,
                    'cohort_id': None,
                    'syllabus_id': None,
                },
                {
                    'academy_id': 1,
                    'allow_shared_creation': False,
                },
                {
                    'academy_id': 1,
                },
            ),
            (
                {
                    'academy_id': 4,
                    'cohort_id': None,
                    'syllabus_id': None,
                },
                {
                    'academy_id': 3,
                    'allow_shared_creation': True,
                },
                {
                    'academy_id': 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(user=1,
                                            event=2,
                                            event_kwargs={'status': 'Active'},
                                            event_type=event_type,
                                            academy=2,
                                            cohort=cohort,
                                            cohort_user=1,
                                            event_type_visibility_setting=event_type_visibility_setting)
            self.bc.request.authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(self, event, model.event_type, model.academy[0], model.user)
                for event in reversed(model.event)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Cohort hunter
    """

    def test_one_item__cohort_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            'academy_id': 2,
            'cohort_id': 2,
            'syllabus_id': None,
        }
        event_type = {
            'academy_id': 1,
            'allow_shared_creation': False,
        }
        cohort = {
            'academy_id': 2,
        }
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        model = self.bc.database.create(user=1,
                                        event=2,
                                        event_type=event_type,
                                        academy=2,
                                        cohort=(2, cohort),
                                        cohort_user=1,
                                        event_type_visibility_setting=event_type_visibility_setting)
        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_one_item__cohort_visible(self):
        cases = [
            (
                {
                    'academy_id': 1,
                    'cohort_id': 1,
                    'syllabus_id': None,
                },
                {
                    'academy_id': 1,
                    'allow_shared_creation': False,
                },
                {
                    'academy_id': 1,
                },
            ),
            (
                {
                    'academy_id': 4,
                    'cohort_id': 2,
                    'syllabus_id': None,
                },
                {
                    'academy_id': 3,
                    'allow_shared_creation': True,
                },
                {
                    'academy_id': 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(user=1,
                                            event=2,
                                            event_kwargs={'status': 'Active'},
                                            event_type=event_type,
                                            academy=2,
                                            cohort=cohort,
                                            cohort_user=1,
                                            event_type_visibility_setting=event_type_visibility_setting)
            self.bc.request.authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(self, event, model.event_type, model.academy[0], model.user)
                for event in reversed(model.event)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Syllabus hunter
    """

    def test_one_item__syllabus_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            'academy_id': 2,
            'cohort_id': None,
            'syllabus_id': 2,
        }
        event_type = {
            'academy_id': 1,
            'allow_shared_creation': False,
        }
        cohort = {
            'academy_id': 2,
        }
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        model = self.bc.database.create(user=1,
                                        event=2,
                                        event_type=event_type,
                                        academy=2,
                                        cohort=(2, cohort),
                                        cohort_user=1,
                                        syllabus=2,
                                        syllabus_version=1,
                                        event_type_visibility_setting=event_type_visibility_setting)
        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_one_item__syllabus_visible(self):
        cases = [
            (
                {
                    'academy_id': 1,
                    'cohort_id': None,
                    'syllabus_id': 1,
                },
                {
                    'academy_id': 1,
                    'allow_shared_creation': False,
                },
                {
                    'academy_id': 1,
                },
            ),
            (
                {
                    'academy_id': 4,
                    'cohort_id': None,
                    'syllabus_id': 2,
                },
                {
                    'academy_id': 3,
                    'allow_shared_creation': True,
                },
                {
                    'academy_id': 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(user=1,
                                            event=2,
                                            event_kwargs={'status': 'Active'},
                                            event_type=event_type,
                                            academy=2,
                                            cohort=cohort,
                                            cohort_user=1,
                                            syllabus=1,
                                            syllabus_version=1,
                                            event_type_visibility_setting=event_type_visibility_setting)

            self.bc.request.authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(self, event, model.event_type, model.academy[0], model.user)
                for event in reversed(model.event)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    def test_one_item__status_not_active(self):
        cases = [
            (
                {
                    'academy_id': 1,
                    'cohort_id': None,
                    'syllabus_id': 1,
                },
                {
                    'academy_id': 1,
                    'allow_shared_creation': False,
                },
                {
                    'academy_id': 1,
                },
            ),
            (
                {
                    'academy_id': 4,
                    'cohort_id': None,
                    'syllabus_id': 2,
                },
                {
                    'academy_id': 3,
                    'allow_shared_creation': True,
                },
                {
                    'academy_id': 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy('events:me')
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(user=1,
                                            event=2,
                                            event_type=event_type,
                                            academy=2,
                                            cohort=cohort,
                                            cohort_user=1,
                                            syllabus=1,
                                            syllabus_version=1,
                                            event_type_visibility_setting=event_type_visibility_setting)

            self.bc.request.authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)
