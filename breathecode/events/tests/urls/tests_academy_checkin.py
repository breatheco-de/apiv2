import re

from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from unittest.mock import MagicMock, call, patch

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_academy_checkin_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_checkin')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_checkin_without_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_checkin')
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_eventcheckin for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    def test_academy_checkin_without_data(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_eventcheckin',
                                     role='potato')
        url = reverse_lazy('events:academy_checkin')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_checkin_with_bad_academy(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        model = self.generate_models(event_checkin=True, event_kwargs=event_kwargs, models=base)
        url = reverse_lazy('events:academy_checkin')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin__(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        event_checkin_kwargs = {'attended_at': self.datetime_now()}
        model = self.generate_models(event=True,
                                     event_checkin=True,
                                     event_kwargs=event_kwargs,
                                     models=base,
                                     event_checkin_kwargs=event_checkin_kwargs)
        url = reverse_lazy('events:academy_checkin')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'attendee': {
                'first_name': model['event_checkin'].attendee.first_name,
                'id': model['event_checkin'].attendee.id,
                'last_name': model['event_checkin'].attendee.last_name
            },
            'email': model['event_checkin'].email,
            'event': {
                'ending_at': self.datetime_to_iso(model['event_checkin'].event.ending_at),
                'event_type': model['event_checkin'].event.event_type,
                'id': model['event_checkin'].event.id,
                'starting_at': self.datetime_to_iso(model['event_checkin'].event.starting_at),
                'title': model['event_checkin'].event.title
            },
            'id': model['event_checkin'].id,
            'status': model['event_checkin'].status,
            'created_at': self.datetime_to_iso(model['event_checkin'].created_at),
            'attended_at': self.datetime_to_iso(model['event_checkin'].attended_at)
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_bad_status(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        model = self.generate_models(event=True, event_checkin=True, event_kwargs=event_kwargs, models=base)
        url = reverse_lazy('events:academy_checkin') + '?status=DONE'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_status(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        event_checkin_kwargs = {'attended_at': self.datetime_now()}
        model = self.generate_models(event=True,
                                     event_checkin=True,
                                     event_kwargs=event_kwargs,
                                     models=base,
                                     event_checkin_kwargs=event_checkin_kwargs)
        url = reverse_lazy('events:academy_checkin') + '?status=PENDING'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'attendee': {
                'first_name': model['event_checkin'].attendee.first_name,
                'id': model['event_checkin'].attendee.id,
                'last_name': model['event_checkin'].attendee.last_name
            },
            'email': model['event_checkin'].email,
            'event': {
                'ending_at': self.datetime_to_iso(model['event_checkin'].event.ending_at),
                'event_type': model['event_checkin'].event.event_type,
                'id': model['event_checkin'].event.id,
                'starting_at': self.datetime_to_iso(model['event_checkin'].event.starting_at),
                'title': model['event_checkin'].event.title
            },
            'id': model['event_checkin'].id,
            'status': model['event_checkin'].status,
            'created_at': self.datetime_to_iso(model['event_checkin'].created_at),
            'attended_at': self.datetime_to_iso(model['event_checkin'].attended_at)
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_bad_event(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        model = self.generate_models(event=True, event_checkin=True, event_kwargs=event_kwargs, models=base)
        url = reverse_lazy('events:academy_checkin') + '?event=2'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_event(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        event_checkin_kwargs = {'attended_at': self.datetime_now()}
        model = self.generate_models(event=True,
                                     event_checkin=True,
                                     event_kwargs=event_kwargs,
                                     models=base,
                                     event_checkin_kwargs=event_checkin_kwargs)
        url = reverse_lazy('events:academy_checkin') + '?event=1'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'attendee': {
                'first_name': model['event_checkin'].attendee.first_name,
                'id': model['event_checkin'].attendee.id,
                'last_name': model['event_checkin'].attendee.last_name
            },
            'email': model['event_checkin'].email,
            'event': {
                'ending_at': self.datetime_to_iso(model['event_checkin'].event.ending_at),
                'event_type': model['event_checkin'].event.event_type,
                'id': model['event_checkin'].event.id,
                'starting_at': self.datetime_to_iso(model['event_checkin'].event.starting_at),
                'title': model['event_checkin'].event.title
            },
            'id': model['event_checkin'].id,
            'status': model['event_checkin'].status,
            'created_at': self.datetime_to_iso(model['event_checkin'].created_at),
            'attended_at': self.datetime_to_iso(model['event_checkin'].attended_at)
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_bad_start(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        model = self.generate_models(event=True, event_checkin=True, event_kwargs=event_kwargs, models=base)
        url = reverse_lazy('events:academy_checkin') + '?start=3000-01-01'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_start(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        event_checkin_kwargs = {'attended_at': self.datetime_now()}
        model = self.generate_models(event=True,
                                     event_checkin=True,
                                     event_kwargs=event_kwargs,
                                     models=base,
                                     event_checkin_kwargs=event_checkin_kwargs)
        date = model['event_checkin'].created_at
        url = (reverse_lazy('events:academy_checkin') + f'?start={date.year}-{date.month}-{date.day}')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'attendee': {
                'first_name': model['event_checkin'].attendee.first_name,
                'id': model['event_checkin'].attendee.id,
                'last_name': model['event_checkin'].attendee.last_name
            },
            'email': model['event_checkin'].email,
            'event': {
                'ending_at': self.datetime_to_iso(model['event_checkin'].event.ending_at),
                'event_type': model['event_checkin'].event.event_type,
                'id': model['event_checkin'].event.id,
                'starting_at': self.datetime_to_iso(model['event_checkin'].event.starting_at),
                'title': model['event_checkin'].event.title
            },
            'id': model['event_checkin'].id,
            'status': model['event_checkin'].status,
            'created_at': self.datetime_to_iso(model['event_checkin'].created_at),
            'attended_at': self.datetime_to_iso(model['event_checkin'].attended_at)
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_bad_end(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        model = self.generate_models(event=True, event_checkin=True, event_kwargs=event_kwargs, models=base)
        url = reverse_lazy('events:academy_checkin') + '?end=1000-01-01'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    def test_academy_checkin_with_end(self):
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_eventcheckin',
                                    role='potato')

        event_kwargs = {'academy': base['academy']}
        event_checkin_kwargs = {'attended_at': self.datetime_now()}
        model = self.generate_models(event=True,
                                     event_checkin=True,
                                     event_kwargs=event_kwargs,
                                     models=base,
                                     event_checkin_kwargs=event_checkin_kwargs)
        date = model['event_checkin'].updated_at
        url = (reverse_lazy('events:academy_checkin') + f'?end={date.year + 1}-{date.month}-{date.day}')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'attendee': {
                'first_name': model['event_checkin'].attendee.first_name,
                'id': model['event_checkin'].attendee.id,
                'last_name': model['event_checkin'].attendee.last_name
            },
            'email': model['event_checkin'].email,
            'event': {
                'ending_at': self.datetime_to_iso(model['event_checkin'].event.ending_at),
                'event_type': model['event_checkin'].event.event_type,
                'id': model['event_checkin'].event.id,
                'starting_at': self.datetime_to_iso(model['event_checkin'].event.starting_at),
                'title': model['event_checkin'].event.title
            },
            'id': model['event_checkin'].id,
            'status': model['event_checkin'].status,
            'created_at': self.datetime_to_iso(model['event_checkin'].created_at),
            'attended_at': self.datetime_to_iso(model['event_checkin'].attended_at)
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_event_checkin_dict(), [{**self.model_to_dict(model, 'event_checkin')}])

    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_academy_checkin__spy_extensions(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_eventcheckin',
                                     role='potato')
        url = reverse_lazy('events:academy_checkin')

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension', 'SortExtension']),
        ])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_academy_checkin__spy_extension_arguments(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_eventcheckin',
                                     role='potato')
        url = reverse_lazy('events:academy_checkin')

        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])
