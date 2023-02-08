from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from django.utils import timezone


def get_serializer(event_type, academy=None, city=None, data={}):
    academy_serialized = None
    city_serialized = None

    if city:
        city_serialized = {
            'name': city.name,
        }

    if academy:
        academy_serialized = {
            'city': city_serialized,
            'id': academy.id,
            'name': academy.name,
            'slug': academy.slug,
        }

    return {
        'academy': academy_serialized,
        'id': event_type.id,
        'name': event_type.name,
        'slug': event_type.slug,
        'lang': event_type.lang,
        'description': event_type.description,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_all_academy_events_no_auth(self):

        url = reverse_lazy('events:academy_eventype')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_event_type_no_results(self):
        self.bc.request.set_headers(academy=1)

        # TODO: this is bad placed
        url = reverse_lazy('events:academy_eventype')
        self.generate_models(authenticate=True, profile_academy=1, role=1, capability='read_event_type')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_event_type_with_results(self):
        self.bc.request.set_headers(academy=1)

        # TODO: this is bad placed
        url = reverse_lazy('events:academy_eventype')
        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_event_type')

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])

    def test_bad_academy_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy('events:academy_eventype') + '?academy=banana'
        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_event_type')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])

    def test_properly_academy_slug(self):
        self.bc.request.set_headers(academy=1)

        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     academy=1,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_event_type')
        url = reverse_lazy('events:academy_eventype') + f'?academy={model.academy.slug}'

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])

    def test_bad_allow_shared_creation_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy('events:academy_eventype') + '?allow_shared_creation=false'
        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_event_type')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])

    def test_properly_allow_shared_creation_slug(self):
        self.bc.request.set_headers(academy=1)

        event_type_kwargs = {
            'slug': 'potato',
            'name': 'Potato',
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }
        model = self.generate_models(authenticate=True,
                                     academy=1,
                                     event=True,
                                     event_type=True,
                                     event_type_kwargs=event_type_kwargs,
                                     profile_academy=1,
                                     role=1,
                                     capability='read_event_type')
        url = reverse_lazy('events:academy_eventype') + f'?allow_shared_creation=true'

        response = self.client.get(url)
        json = response.json()
        print(json)
        expected = [get_serializer(model.event_type, model.academy, model.city)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.all_event_type_dict(), [{
            **self.model_to_dict(model, 'event_type'),
        }])
