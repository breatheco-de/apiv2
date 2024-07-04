from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from breathecode.services import datetime_to_iso_format
from django.utils import timezone


def get_serializer(visibility_setting, academy=None, city=None, data={}):

    return {
        "id": visibility_setting.id,
        "academy": {
            "id": visibility_setting.academy.id,
            "name": visibility_setting.academy.name,
            "slug": visibility_setting.academy.slug,
        },
        "cohort": (
            {
                "id": visibility_setting.cohort.id,
                "name": visibility_setting.cohort.name,
                "slug": visibility_setting.cohort.slug,
            }
            if visibility_setting.cohort
            else None
        ),
        "syllabus": (
            {
                "id": visibility_setting.syllabus.id,
                "name": visibility_setting.syllabus.name,
                "slug": visibility_setting.syllabus.slug,
            }
            if visibility_setting.syllabus
            else None
        ),
        **data,
    }


class AcademyEventTypeVisibilitySettingsTestSuite(EventTestCase):
    cache = EventCache()

    def test_delete_event_type_vs_no_auth(self):

        url = reverse_lazy(
            "events:academy_eventype_slug_visibilitysetting_id",
            kwargs={"event_type_slug": "funny_event", "visibility_setting_id": 1},
        )

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_delete_visibilitysetting_with_bad_id(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy(
            "events:academy_eventype_slug_visibilitysetting_id",
            kwargs={"event_type_slug": "funny_event", "visibility_setting_id": 2},
        )
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com", "visibility_settings": 1},
            event_type_visibility_setting=True,
        )

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "event-type-visibility-setting-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [1])
        self.assertEqual(
            self.bc.database.list_of("events.EventTypeVisibilitySetting"),
            [{"id": 1, "academy_id": 1, "syllabus_id": None, "cohort_id": 1}],
        )

    def test_delete_visibilitysetting_with_bad_slug(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy(
            "events:academy_eventype_slug_visibilitysetting_id",
            kwargs={"event_type_slug": "funny_event", "visibility_setting_id": 1},
        )
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type_visibility_setting=True,
            event_type={"slug": "kenny", "icon_url": "https://www.google.com", "visibility_settings": 1},
        )

        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "event-type-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [1])
        self.assertEqual(
            self.bc.database.list_of("events.EventTypeVisibilitySetting"),
            [{"id": 1, "academy_id": 1, "syllabus_id": None, "cohort_id": 1}],
        )

    def test_delete_visibilitysetting_with_no_other_event_type(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy(
            "events:academy_eventype_slug_visibilitysetting_id",
            kwargs={"event_type_slug": "funny_event", "visibility_setting_id": 1},
        )
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type_visibility_setting=True,
            event_type={"slug": "funny_event", "icon_url": "https://www.google.com"},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.bc.check.queryset_with_pks(model.event_type.visibility_settings.all(), [])
        self.assertEqual(self.bc.database.list_of("events.EventTypeVisibilitySetting"), [])

    def test_delete_visibilitysetting_with_other_event_type(self):
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy(
            "events:academy_eventype_slug_visibilitysetting_id",
            kwargs={"event_type_slug": "funny_event", "visibility_setting_id": 1},
        )
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_event_type",
            event_type_visibility_setting=True,
            event_type=[
                {"slug": "funny_event", "icon_url": "https://www.google.com", "visibility_settings": 1},
                {"slug": "great_event", "icon_url": "https://www.google.com", "visibility_settings": 1},
            ],
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.bc.check.queryset_with_pks(model.event_type[1].visibility_settings.all(), [1])
        self.assertEqual(
            self.bc.database.list_of("events.EventTypeVisibilitySetting"),
            [{"id": 1, "academy_id": 1, "syllabus_id": None, "cohort_id": 1}],
        )
