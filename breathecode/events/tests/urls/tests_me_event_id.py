import random
import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy

from breathecode.events.caches import EventCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ..mixins.new_events_tests_case import EventTestCase


def visibility_settings_serializer(visibility_settings):
    all_vs = visibility_settings.all()

    serialized_vs = [
        {
            "id": item.id,
            "cohort": (
                {
                    "id": item.cohort.id,
                    "name": item.cohort.name,
                    "slug": item.cohort.slug,
                }
                if item.cohort
                else None
            ),
            "academy": {
                "id": item.academy.id,
                "name": item.academy.name,
                "slug": item.academy.slug,
            },
            "syllabus": (
                {
                    "id": item.syllabus.id,
                    "name": item.syllabus.name,
                    "slug": item.syllabus.slug,
                }
                if item.syllabus
                else None
            ),
        }
        for item in all_vs
    ]
    return serialized_vs


def profile_translation_serializer(profile_translation):
    return {
        "bio": profile_translation.bio,
        "lang": profile_translation.lang,
    }


def profile_serializer(profile, profile_translations=[]):
    return {
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "blog": profile.blog,
        "github_username": profile.github_username,
        "linkedin_url": profile.linkedin_url,
        "phone": profile.phone,
        "portfolio_url": profile.portfolio_url,
        "translations": [profile_translation_serializer(item) for item in profile_translations],
        "twitter_username": profile.twitter_username,
    }


def get_serializer(
    self, event, event_type, user, academy=None, city=None, profile=None, profile_translations=[], data={}
):
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
        "author": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "host_user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile": profile_serializer(profile, profile_translations) if profile else None,
        },
        "banner": event.banner,
        "capacity": event.capacity,
        "free_for_bootcamps": event.free_for_bootcamps,
        "free_for_all": event.free_for_all,
        "live_stream_url": event.live_stream_url,
        "asset_slug": event.asset_slug,
        "asset": None,
        "created_at": self.bc.datetime.to_iso_string(event.created_at),
        "currency": event.currency,
        "description": event.description,
        "ending_at": self.bc.datetime.to_iso_string(event.ending_at),
        "ended_at": event.ended_at,
        "event_type": {
            "academy": academy_serialized,
            "id": event_type.id,
            "name": event_type.name,
            "slug": event_type.slug,
            "lang": event_type.lang,
            "icon_url": event_type.icon_url,
            "allow_shared_creation": event_type.allow_shared_creation,
            "description": event_type.description,
            "visibility_settings": visibility_settings_serializer(event_type.visibility_settings),
            "technologies": event_type.technologies,
        },
        "eventbrite_id": event.eventbrite_id,
        "eventbrite_organizer_id": event.eventbrite_organizer_id,
        "eventbrite_status": event.eventbrite_status,
        "eventbrite_sync_description": event.eventbrite_sync_description,
        "eventbrite_sync_status": event.eventbrite_sync_status,
        "eventbrite_url": event.eventbrite_url,
        "excerpt": event.excerpt,
        "host": event.host,
        "id": event.id,
        "lang": event.lang,
        "online_event": event.online_event,
        "organization": event.organization,
        "published_at": event.published_at,
        "slug": event.slug,
        "starting_at": self.bc.datetime.to_iso_string(event.starting_at),
        "status": event.status,
        "sync_with_eventbrite": event.sync_with_eventbrite,
        "tags": event.tags,
        "title": event.title,
        "updated_at": self.bc.datetime.to_iso_string(event.updated_at),
        "url": event.url,
        "venue": event.venue,
        "is_public": event.is_public,
        **data,
    }


def extract_starting_at(d):
    return datetime.strptime(str(d.starting_at), "%Y-%m-%d %H:%M:%S%z")


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    # When: no auth
    # Then: return 401
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    # When: zero Event
    # Then: return 404
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_zero_items(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.bc.database.list_of("events.Event"), [])

    # Given: 1 Event, 1 EventType and 1 User
    # When: No EventTypeVisibilitySetting
    # Then: return 404
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_no_visible(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        model = self.bc.database.create(user=1, event=1, event_type={"icon_url": "https://www.google.com"})
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

    # Given: 1 Event, 1 EventType, 1 User, 1 Academy and 1 CohortUser
    # When: visible in this cohort
    # Then: return 200
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_visible_in_this_cohort(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        event_type_visibility_setting = {"cohort_id": 1, "syllabus_id": None, "academy_id": 1}

        model = self.bc.database.create(
            user=1,
            event=1,
            event_type={"icon_url": "https://www.google.com"},
            event_type_visibility_setting=event_type_visibility_setting,
            cohort_user=1,
            academy=1,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(
            self, model.event, model.event_type, model.user, academy=model.academy, city=model.city, data={}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

    # Given: 1 Event, 1 EventType, 1 User, 1 Academy and 1 CohortUser
    # When: visible in this academy
    # Then: return 200
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_visible_in_this_academy(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        event_type_visibility_setting = {"cohort_id": None, "syllabus_id": None, "academy_id": 1}

        model = self.bc.database.create(
            user=1,
            event=1,
            event_type={"icon_url": "https://www.google.com"},
            event_type_visibility_setting=event_type_visibility_setting,
            cohort_user=1,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(
            self, model.event, model.event_type, model.user, academy=model.academy, city=model.city, data={}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

    # Given: 1 Event, 1 EventType, 1 User, 1 Academy and 1 CohortUser
    # When: visible in this academy
    # Then: return 200
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_visible_in_this_syllabus(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        event_type_visibility_setting = {"cohort_id": None, "syllabus_id": 1, "academy_id": 1}

        model = self.bc.database.create(
            user=1,
            event=1,
            academy=1,
            event_type={"icon_url": "https://www.google.com"},
            event_type_visibility_setting=event_type_visibility_setting,
            cohort_user=1,
            syllabus=1,
            syllabus_version=1,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(
            self, model.event, model.event_type, model.user, academy=model.academy, city=model.city, data={}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

    # Given: 1 Event, 1 EventType, 1 EventTypeSet, 1 User, 1 Academy and 1 Subscription
    # When: visible in this subscription
    # Then: return 200
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_visible_in_this_subscription(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        model = self.bc.database.create(
            user=1,
            event=1,
            academy=1,
            event_type={"icon_url": "https://www.google.com"},
            event_type_set=1,
            subscription=1,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(
            self, model.event, model.event_type, model.user, academy=model.academy, city=model.city, data={}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )

    # Given: 1 Event, 1 EventType, 1 EventTypeSet, 1 User, 1 Academy, 1 PlanFinancing,
    #     -> 1 Profile and 2 ProfileTranslation
    # When: visible in this plan financing
    # Then: return 200
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_visible_in_this_plan_financing(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me_event_id", kwargs={"event_id": 1})

        plan_financing = {
            "plan_expires_at": datetime.now() + timedelta(days=1),
            "monthly_price": random.random() * 100,
            "valid_until": datetime.now() + timedelta(days=1),
        }

        model = self.bc.database.create(
            user=1,
            event=1,
            academy=1,
            profile=1,
            profile_translation=2,
            event_type={"icon_url": "https://www.google.com"},
            event_type_set=1,
            plan_financing=plan_financing,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(
            self,
            model.event,
            model.event_type,
            model.user,
            academy=model.academy,
            city=model.city,
            profile=model.profile,
            profile_translations=model.profile_translation,
            data={},
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("events.Event"),
            [
                self.bc.format.to_dict(model.event),
            ],
        )
