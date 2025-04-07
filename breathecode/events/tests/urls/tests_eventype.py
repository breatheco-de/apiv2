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
        "description": event_type.description,
        "technologies": event_type.technologies,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    def test_all_academy_events_no_auth(self):

        url = reverse_lazy("events:eventype")

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_academy_event_type_no_results(self):

        # TODO: this is bad placed
        url = reverse_lazy("events:eventype")
        self.generate_models(authenticate=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    def test_academy_event_type_with_results(self):

        # TODO: this is bad placed
        url = reverse_lazy("events:eventype")
        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
            "technologies": None,
        }
        model = self.generate_models(
            authenticate=True, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

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

    def test_bad_academy_slug(self):

        url = reverse_lazy("events:eventype") + "?academy=banana"
        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }
        model = self.generate_models(
            authenticate=True, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )

        response = self.client.get(url)
        json = response.json()
        expected = []

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

    def test_properly_academy_slug(self):

        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }
        model = self.generate_models(
            authenticate=True, academy=1, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )
        url = reverse_lazy("events:eventype") + f"?academy={model.academy.slug}"

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

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

    def test_bad_allow_shared_creation_slug(self):

        url = reverse_lazy("events:eventype") + "?allow_shared_creation=false"
        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }
        model = self.generate_models(
            authenticate=True, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )

        response = self.client.get(url)
        json = response.json()
        expected = []

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

    def test_properly_allow_shared_creation_slug(self):

        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
        }
        model = self.generate_models(
            authenticate=True, academy=1, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )
        url = reverse_lazy("events:eventype") + f"?allow_shared_creation=true"

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

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

    def test_filter_by_lang_en_with_results(self):
        """Test filtering event types by lang=en and getting results"""

        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
            "lang": "en",  # setting lang to en specifically
            "technologies": None,
        }
        model = self.generate_models(
            authenticate=True, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )
        url = reverse_lazy("events:eventype") + "?lang=en"

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.event_type, model.academy, model.city)]

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

    def test_filter_by_lang_es_no_results(self):
        """Test filtering event types by lang=es and getting empty results"""

        event_type_kwargs = {
            "slug": "potato",
            "name": "Potato",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "icon_url": "https://www.google.com",
            "lang": "en",  # setting lang to en, so filtering by es should return empty
            "technologies": None,
        }
        model = self.generate_models(
            authenticate=True, event=True, event_type=True, event_type_kwargs=event_type_kwargs
        )
        url = reverse_lazy("events:eventype") + "?lang=es"

        response = self.client.get(url)
        json = response.json()
        expected = []  # Empty array because no event type has lang=es

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        # Verify the model still exists in database but wasn't returned in results
        self.assertEqual(
            self.all_event_type_dict(),
            [
                {
                    **self.model_to_dict(model, "event_type"),
                }
            ],
        )
