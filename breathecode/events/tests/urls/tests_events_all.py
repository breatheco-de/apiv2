import os
from unittest.mock import MagicMock, PropertyMock, call, patch
from uuid import UUID

from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.events.caches import EventCache
from breathecode.services import datetime_to_iso_format
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins.new_events_tests_case import EventTestCase

seed = os.urandom(16)
uuid = UUID(bytes=seed, version=4)


def post_serializer(data={}):
    return {
        "tags": "",
        "url": "",
        "banner": "",
        "capacity": 0,
        "starting_at": ...,
        "ending_at": ...,
        "academy": 0,
        "author": None,
        "description": None,
        "free_for_bootcamps": None,
        "event_type": None,
        "eventbrite_id": None,
        "eventbrite_organizer_id": None,
        "eventbrite_status": None,
        "eventbrite_url": None,
        "slug": None,
        "excerpt": None,
        "host": None,
        "id": 0,
        "lang": None,
        "online_event": False,
        "live_stream_url": None,
        "free_for_bootcamps": True,
        "asset_slug": None,
        "ended_at": None,
        "organization": 0,
        "published_at": None,
        "status": "DRAFT",
        "eventbrite_sync_description": None,
        "eventbrite_sync_status": "PENDING",
        "title": None,
        "venue": None,
        "sync_with_eventbrite": False,
        "currency": "USD",
        "live_stream_url": None,
        "host_user": None,
        "is_public": True,
        **data,
    }


def event_table(data={}):
    return {
        "academy_id": 0,
        "author_id": None,
        "banner": "",
        "capacity": 0,
        "description": None,
        "ending_at": ...,
        "event_type_id": None,
        "eventbrite_id": None,
        "eventbrite_organizer_id": None,
        "eventbrite_status": None,
        "eventbrite_url": None,
        "free_for_bootcamps": None,
        "excerpt": None,
        "tags": "",
        "slug": None,
        "host": None,
        "id": 0,
        "lang": None,
        "online_event": False,
        "live_stream_url": None,
        "free_for_bootcamps": True,
        "asset_slug": None,
        "organization_id": 0,
        "host_user_id": None,
        "published_at": None,
        "starting_at": ...,
        "status": "DRAFT",
        "eventbrite_sync_description": None,
        "eventbrite_sync_status": "",
        "title": None,
        "ended_at": None,
        "url": "",
        "venue_id": None,
        "live_stream_url": None,
        "sync_with_eventbrite": False,
        "currency": "",
        "is_public": True,
        **data,
    }


def test_all_events_get_all_events_with_is_public_true(self):
    self.headers(academy=1)

    model = self.generate_models(
        authenticate=True,
        profile_academy=True,
        capability="read_event",
        role="potato",
        syllabus=True,
        venue=True,
        event=True,
        is_public=True,
    )

    url = reverse_lazy("events:all_events")

    response = self.client.get(url)
    json = response.json()

    expected = [
        {
            "banner": model["event"].banner,
            "ending_at": datetime_to_iso_format(model["event"].ending_at),
            "event_type": model["event"].event_type,
            "excerpt": model["event"].excerpt,
            "tags": model["event"].tags,
            "slug": model["event"].slug,
            "id": model["event"].id,
            "lang": model["event"].lang,
            "online_event": model["event"].online_event,
            "starting_at": datetime_to_iso_format(model["event"].starting_at),
            "ended_at": model["event"].ended_at,
            "status": model["event"].status,
            "title": model["event"].title,
            "url": model["event"].url,
            "host": model["event"].host,
            "asset_slug": model["event"].asset_slug,
            "capacity": model["event"].capacity,
            "venue": {
                "city": model["event"].venue.city,
                "id": model["event"].id,
                "state": model["event"].venue.state,
                "street_address": model["event"].venue.street_address,
                "title": model["event"].venue.title,
                "zip_code": model["event"].venue.zip_code,
                "updated_at": self.bc.datetime.to_iso_string(model["venue"].updated_at),
            },
            "sync_with_eventbrite": model["event"].sync_with_eventbrite,
            "eventbrite_sync_description": model["event"].eventbrite_sync_description,
            "eventbrite_sync_status": model["event"].eventbrite_sync_status,
            "is_public": model["event"].is_public,
        }
    ]

    self.assertEqual(json, expected)
    self.assertEqual(response.status_code, 200)


def test_all_events_get_all_events_with_is_public_false(self):
    self.headers(academy=1)

    model = self.generate_models(
        authenticate=True,
        profile_academy=True,
        capability="read_event",
        role="potato",
        syllabus=True,
        venue=True,
        event=True,
        is_public=True,
    )

    url = reverse_lazy("events:all_events")

    response = self.client.get(url)
    json = response.json()

    expected = [
        {
            "banner": model["event"].banner,
            "ending_at": datetime_to_iso_format(model["event"].ending_at),
            "event_type": model["event"].event_type,
            "excerpt": model["event"].excerpt,
            "tags": model["event"].tags,
            "slug": model["event"].slug,
            "id": model["event"].id,
            "lang": model["event"].lang,
            "online_event": model["event"].online_event,
            "starting_at": datetime_to_iso_format(model["event"].starting_at),
            "ended_at": model["event"].ended_at,
            "status": model["event"].status,
            "title": model["event"].title,
            "url": model["event"].url,
            "host": model["event"].host,
            "asset_slug": model["event"].asset_slug,
            "capacity": model["event"].capacity,
            "venue": {
                "city": model["event"].venue.city,
                "id": model["event"].id,
                "state": model["event"].venue.state,
                "street_address": model["event"].venue.street_address,
                "title": model["event"].venue.title,
                "zip_code": model["event"].venue.zip_code,
                "updated_at": self.bc.datetime.to_iso_string(model["venue"].updated_at),
            },
            "sync_with_eventbrite": model["event"].sync_with_eventbrite,
            "eventbrite_sync_description": model["event"].eventbrite_sync_description,
            "eventbrite_sync_status": model["event"].eventbrite_sync_status,
            "is_public": model["event"].is_public,
        }
    ]

    self.assertEqual(json, expected)
    self.assertEqual(response.status_code, 200)


def test_all_events_get_all_events_with_is_public_empty(self):
    self.headers(academy=1)

    model = self.generate_models(
        authenticate=True,
        profile_academy=True,
        capability="read_event",
        role="potato",
        syllabus=True,
        venue=True,
        event=True,
    )

    url = reverse_lazy("events:all_events")

    response = self.client.get(url)
    json = response.json()

    expected = [
        {
            "banner": model["event"].banner,
            "ending_at": datetime_to_iso_format(model["event"].ending_at),
            "event_type": model["event"].event_type,
            "excerpt": model["event"].excerpt,
            "tags": model["event"].tags,
            "slug": model["event"].slug,
            "id": model["event"].id,
            "lang": model["event"].lang,
            "online_event": model["event"].online_event,
            "starting_at": datetime_to_iso_format(model["event"].starting_at),
            "ended_at": model["event"].ended_at,
            "status": model["event"].status,
            "title": model["event"].title,
            "url": model["event"].url,
            "host": model["event"].host,
            "asset_slug": model["event"].asset_slug,
            "capacity": model["event"].capacity,
            "venue": {
                "city": model["event"].venue.city,
                "id": model["event"].id,
                "state": model["event"].venue.state,
                "street_address": model["event"].venue.street_address,
                "title": model["event"].venue.title,
                "zip_code": model["event"].venue.zip_code,
                "updated_at": self.bc.datetime.to_iso_string(model["venue"].updated_at),
            },
            "sync_with_eventbrite": model["event"].sync_with_eventbrite,
            "eventbrite_sync_description": model["event"].eventbrite_sync_description,
            "eventbrite_sync_status": model["event"].eventbrite_sync_status,
            "is_public": model["event"].is_public,
        }
    ]

    self.assertEqual(json, expected)
    self.assertEqual(response.status_code, 200)
