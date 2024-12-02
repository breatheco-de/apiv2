from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.events.caches import EventCache
from breathecode.services import datetime_to_iso_format
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins.new_events_tests_case import EventTestCase


def get_serializer(event_type, academy=None, city=None, data={}):
    academy_serialized = None
    city_serialized = None

    if city:
        city_serialized = {
            "name": city.name,
        }

    if academy:
        academy_serialized = {
            "city": city_serialized,
            "id": academy.id,
            "name": academy.name,
            "slug": academy.slug,
        }

    return {
        "academy": academy_serialized,
        "id": event_type.id,
        "name": event_type.name,
        "slug": event_type.slug,
        "lang": event_type.lang,
        "icon_url": event_type.icon_url,
        "allow_shared_creation": event_type.allow_shared_creation,
        "description": event_type.description,
        "visibility_settings": event_type.visibility_settings,
        "technologies": event_type.technologies,
        **data,
    }


def put_serializer(event_type, data={}):

    return {
        "academy": event_type.academy,
        "id": event_type.id,
        "name": event_type.name,
        "slug": event_type.slug,
        "lang": event_type.lang,
        "icon_url": event_type.icon_url,
        "allow_shared_creation": event_type.allow_shared_creation,
        "free_for_bootcamps": event_type.free_for_bootcamps,
        "description": event_type.description,
        "technologies": event_type.technologies,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_academy_event_type_slug_no_auth(self):

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "funny_event"})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_event_type_with_bad_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "funny_event"})
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_event_type",
        )

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "event-type-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    def test_academy_event_type_with_results(self):
        self.bc.request.set_headers(academy=1)

        event_type_slug = "potato"
        event_type_kwargs = {
            "slug": event_type_slug,
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": event_type_slug})
        model = self.generate_models(
            authenticate=True,
            event=True,
            event_type=True,
            event_type_kwargs=event_type_kwargs,
            profile_academy=1,
            role=1,
            capability="read_event_type",
        )

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(model.event_type, model.academy, model.city, {"visibility_settings": []})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.all_event_type_dict(),
            [
                {
                    **self.model_to_dict(model, "event_type"),
                }
            ],
        )

    def test_academy_event_type_slug__put(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        event_type_slug = "potato"
        event_type_kwargs = {
            "slug": event_type_slug,
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }

        model = self.generate_models(
            authenticate=True,
            event=True,
            event_type=True,
            event_type_kwargs=event_type_kwargs,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
        )

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "potato"})
        current_date = self.datetime_now()
        data = {
            "id": 1,
            "slug": "potato",
            "name": "SUPER NEW event type changed",
            "description": "funtastic event type",
        }

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        self.assertDatetime(json["updated_at"])

        del json["created_at"]
        del json["updated_at"]

        expected = put_serializer(model.event_type, {**data, "visibility_settings": [], "academy": 1})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.bc.database.list_of("events.EventType"), self.bc.format.to_dict(model.event_type))

    def test_academy_event_type_slug__put_with_bad_slug(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        event_type_slug = "potato"
        event_type_kwargs = {
            "slug": event_type_slug,
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }

        model = self.generate_models(
            authenticate=True,
            event=True,
            event_type=True,
            event_type_kwargs=event_type_kwargs,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
        )

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "potattto"})
        current_date = self.datetime_now()
        data = {
            "id": 1,
            "slug": "potato",
            "name": "SUPER NEW event type changed",
            "description": "funtastic event type",
        }

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = {"detail": "event-type-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    def test_academy_event_type_slug_put_without_icon_url(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        event_type_slug = "potato"
        event_type_kwargs = {
            "slug": event_type_slug,
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }

        model = self.generate_models(
            authenticate=True,
            event=True,
            event_type=True,
            event_type_kwargs=event_type_kwargs,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
        )

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "potato"})
        current_date = self.datetime_now()
        data = {
            "id": 1,
            "slug": "potato",
            "name": "SUPER NEW event type changed",
            "description": "funtastic event type",
        }

        response = self.client.put(url, data, format="json")
        json = response.json()

        expected = {"icon_url": ["This field is required."]}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of("events.EventType"), [{**self.bc.format.to_dict(model.event_type)}])

    def test_academy_event_type_slug__put(self):
        """Test /cohort without auth"""
        self.headers(academy=1)

        event_type_slug = "potato"
        event_type_kwargs = {
            "slug": event_type_slug,
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }

        model = self.generate_models(
            authenticate=True,
            event=True,
            event_type=True,
            event_type_kwargs=event_type_kwargs,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
        )

        url = reverse_lazy("events:academy_eventype_slug", kwargs={"event_type_slug": "potato"})
        current_date = self.datetime_now()
        data = {
            "id": 1,
            "slug": "potato",
            "name": "SUPER NEW event type changed",
            "icon_url": "https://www.google.com",
            "description": "funtastic event type",
        }

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        self.assertDatetime(json["updated_at"])

        del json["created_at"]
        del json["updated_at"]

        expected = put_serializer(model.event_type, {**data, "academy": 1})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.EventType"), [{**self.bc.format.to_dict(model.event_type), **data}]
        )
