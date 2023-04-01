import re
from datetime import datetime, timedelta

from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from unittest.mock import MagicMock, call, patch

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase


def visibility_settings_serializer(visibility_settings):
    all_vs = visibility_settings.all()

    serialized_vs = [{
        'id': item.id,
        'cohort': {
            'id': item.cohort.id,
            'name': item.cohort.name,
            'slug': item.cohort.slug,
        } if item.cohort else None,
        'academy': {
            'id': item.academy.id,
            'name': item.academy.name,
            'slug': item.academy.slug,
        },
        'syllabus': {
            'id': item.syllabus.id,
            'name': item.syllabus.name,
            'slug': item.syllabus.slug,
        } if item.syllabus else None,
    } for item in all_vs]
    return serialized_vs


def get_serializer(self, event, event_type, user, academy=None, city=None, data={}):
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
        'author': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'banner': event.banner,
        'capacity': event.capacity,
        'created_at': self.bc.datetime.to_iso_string(event.created_at),
        'currency': event.currency,
        'description': event.description,
        'ending_at': self.bc.datetime.to_iso_string(event.ending_at),
        'event_type': {
            'academy': academy_serialized,
            'id': event_type.id,
            'name': event_type.name,
            'slug': event_type.slug,
            'lang': event_type.lang,
            'icon_url': event_type.icon_url,
            'allow_shared_creation': event_type.allow_shared_creation,
            'description': event_type.description,
            'visibility_settings': visibility_settings_serializer(event_type.visibility_settings),
        },
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


def extract_starting_at(d):
    return datetime.strptime(str(d.starting_at), '%Y-%m-%d %H:%M:%S%z')


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:me_event_liveclass')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_zero_items(self):
        self.headers(academy=1)

        live_class = {}
        model = self.bc.database.create(user=1, live_class=live_class, cohort=1, cohort_time_slot=1)
        # url = reverse_lazy('events:me_event_liveclass') + '?remote_meeting_url=asdasd'

        date = self.bc.datetime.to_iso_string(model.live_class.ending_at + timedelta(days=1))
        # url = reverse_lazy('events:me_event_liveclass') + f'?start={date}'
        # url = reverse_lazy('events:me_event_liveclass') + f'?end={date}'
        url = reverse_lazy(
            'events:me_event_liveclass') + f'?remote_meeting_url=aa{model.live_class.remote_meeting_url}'
        # url = reverse_lazy('events:me_event_liveclass') + '?start=2023-04-01T14:14:27.752Z'

        # url = reverse_lazy('events:me_event_liveclass') + '?upcoming=true'
        # url = reverse_lazy('events:me_event_liveclass') + f'?cohort={model.cohort.slug}aaa'

        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []
        expected = {}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        # self.bc.datetime.to_iso_string()
        assert 0
