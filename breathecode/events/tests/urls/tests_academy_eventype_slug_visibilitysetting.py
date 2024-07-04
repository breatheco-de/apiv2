from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from django.utils import timezone


def get_serializer(visibility_setting, data={}):

    return {
        "id": visibility_setting["id"],
        "academy": {
            "id": visibility_setting["academy"]["id"],
            "name": visibility_setting["academy"]["name"],
            "slug": visibility_setting["academy"]["slug"],
        },
        "cohort": (
            {
                "id": visibility_setting["cohort"]["id"],
                "name": visibility_setting["cohort"]["name"],
                "slug": visibility_setting["cohort"]["slug"],
            }
            if visibility_setting["cohort"]
            else None
        ),
        "syllabus": (
            {
                "id": visibility_setting["syllabus"]["id"],
                "name": visibility_setting["syllabus"]["name"],
                "slug": visibility_setting["syllabus"]["slug"],
            }
            if visibility_setting["syllabus"]
            else None
        ),
        **data,
    }


class AcademyEventTypeVisibilitySettingsTestSuite(EventTestCase):
    cache = EventCache()

    def test_post_event_type_with_no_auth(self):

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_get_visibilitysetting_with_bad_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_event_type",
        )

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    def test_get_visibilitysetting(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            event_type_visibility_setting=True,
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com", "visibility_settings": 1},
            capability="read_event_type",
        )

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(vs) for vs in json]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [1])

    def test_post_visibilitysetting_with_bad_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
        )

        response = self.client.post(url)
        json = response.json()
        expected = {"detail": "event-type-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    def test_post_visibilitysetting_with_bad_syllabus(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com"},
        )

        data = {"syllabus": 1}
        response = self.client.post(url, data)
        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [])

    def test_post_visibilitysetting_with_bad_cohort(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com"},
        )

        data = {"cohort": 2}
        response = self.client.post(url, data)
        json = response.json()
        expected = {"detail": "cohort-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [])

    def test_post_visibilitysetting(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("events:academy_eventype_slug_visibilitysetting", kwargs={"event_type_slug": "funny_event"})
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com"},
            cohort=True,
            syllabus=True,
        )

        data = {"academy": 1, "syllabus": 1, "cohort": 1}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            "id": 1,
            "academy": {
                "id": model.academy.id,
                "name": model.academy.name,
                "slug": model.academy.slug,
            },
            "cohort": {
                "id": model.cohort.id,
                "name": model.cohort.name,
                "slug": model.cohort.slug,
            },
            "syllabus": {
                "id": model.syllabus.id,
                "name": model.syllabus.name,
                "slug": model.syllabus.slug,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 201)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [1])
        self.assertEqual(
            self.bc.database.list_of("events.EventTypeVisibilitySetting"),
            [{"id": 1, "academy_id": 1, "syllabus_id": 1, "cohort_id": 1}],
        )
