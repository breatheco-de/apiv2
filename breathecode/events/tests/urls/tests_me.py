from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.events.caches import EventCache

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
        "asset": None,
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
        "created_at": self.bc.datetime.to_iso_string(event.created_at),
        "currency": event.currency,
        "description": event.description,
        "ending_at": self.bc.datetime.to_iso_string(event.ending_at),
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
        "free_for_bootcamps": event.free_for_bootcamps,
        "free_for_all": event.free_for_all,
        "live_stream_url": event.live_stream_url,
        "asset_slug": event.asset_slug,
        "organization": event.organization,
        "published_at": event.published_at,
        "slug": event.slug,
        "ended_at": event.ended_at,
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
    return d.starting_at.isoformat()


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me")

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_zero_items(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me")

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__non_visible(self):
        self.headers(academy=1)
        url = reverse_lazy("events:me")

        model = self.bc.database.create(user=1, event=1, event_type={"icon_url": "https://www.google.com"})
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Academy hunter
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__academy_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            "academy_id": 2,
            "cohort_id": None,
            "syllabus_id": None,
        }
        event_type = {
            "academy_id": 1,
            "allow_shared_creation": False,
            "icon_url": "https://www.google.com",
        }
        cohort = {
            "academy_id": 2,
        }
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        model = self.bc.database.create(
            user=1,
            event=2,
            event_type=event_type,
            academy=2,
            cohort=cohort,
            cohort_user=1,
            event_type_visibility_setting=event_type_visibility_setting,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__academy_visible(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 1,
                    "allow_shared_creation": False,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 3,
                    "allow_shared_creation": True,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=2,
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = [
                get_serializer(self, event, model.event_type, model.user, model.academy[0], model.city)
                for event in reversed(model.event)
            ]
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Upcoming=true
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_upcoming_true__two_events__ends_in_the_past(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 1,
                    "allow_shared_creation": False,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 3,
                    "allow_shared_creation": True,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me") + f"?upcoming=true"
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=[
                    {
                        "starting_at": timezone.now() - timedelta(hours=2),
                        "ending_at": timezone.now() - timedelta(hours=1),
                    },
                    {
                        "starting_at": timezone.now() - timedelta(hours=3),
                        "ending_at": timezone.now() - timedelta(hours=2),
                    },
                ],
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = []
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_upcoming_true__two_events__ends_in_the_future(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 1,
                    "allow_shared_creation": False,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 3,
                    "allow_shared_creation": True,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me") + f"?upcoming=true"
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=[
                    {
                        "starting_at": timezone.now() + timedelta(hours=1),
                        "ending_at": timezone.now() + timedelta(hours=2),
                    },
                    {
                        "starting_at": timezone.now() + timedelta(hours=2),
                        "ending_at": timezone.now() + timedelta(hours=3),
                    },
                ],
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = [
                get_serializer(self, event, model.event_type, model.user, model.academy[0], model.city)
                for event in reversed(model.event)
            ]
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Past=true
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_past_true__two_events__ends_in_the_past(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 1,
                    "allow_shared_creation": False,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 3,
                    "allow_shared_creation": True,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me") + f"?past=true"
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=[
                    {
                        "starting_at": timezone.now() - timedelta(hours=2),
                        "ending_at": timezone.now() - timedelta(hours=1),
                    },
                    {
                        "starting_at": timezone.now() - timedelta(hours=3),
                        "ending_at": timezone.now() - timedelta(hours=2),
                    },
                ],
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = [
                get_serializer(self, event, model.event_type, model.user, model.academy[0], model.city)
                for event in reversed(model.event)
            ]
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_past_true__two_events__ends_in_the_future(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 1,
                    "allow_shared_creation": False,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": None,
                },
                {
                    "academy_id": 3,
                    "allow_shared_creation": True,
                    "icon_url": "https://www.google.com",
                },
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me") + f"?past=true"
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=[
                    {
                        "starting_at": timezone.now() + timedelta(hours=1),
                        "ending_at": timezone.now() + timedelta(hours=2),
                    },
                    {
                        "starting_at": timezone.now() + timedelta(hours=2),
                        "ending_at": timezone.now() + timedelta(hours=3),
                    },
                ],
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = []
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Cohort hunter
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__cohort_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            "academy_id": 2,
            "cohort_id": 2,
            "syllabus_id": None,
        }
        event_type = {
            "academy_id": 1,
            "allow_shared_creation": False,
            "icon_url": "https://www.google.com",
        }
        cohort = {
            "academy_id": 2,
        }
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        model = self.bc.database.create(
            user=1,
            event=2,
            event_type=event_type,
            academy=2,
            cohort=(2, cohort),
            cohort_user=1,
            event_type_visibility_setting=event_type_visibility_setting,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__cohort_visible(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": 1,
                    "syllabus_id": None,
                },
                {"academy_id": 1, "allow_shared_creation": False, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": 2,
                    "syllabus_id": None,
                },
                {"academy_id": 3, "allow_shared_creation": True, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=2,
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )
            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = [
                get_serializer(self, event, model.event_type, model.user, model.academy[0], model.city)
                for event in reversed(model.event)
            ]

            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    """
    🥆🥆🥆 Syllabus hunter
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__syllabus_non_visible__because_owner_dont_allow_share_the_event_type(self):
        event_type_visibility_setting = {
            "academy_id": 2,
            "cohort_id": None,
            "syllabus_id": 2,
        }
        event_type = {"academy_id": 1, "allow_shared_creation": False, "icon_url": "https://www.google.com"}
        cohort = {
            "academy_id": 2,
        }
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        model = self.bc.database.create(
            user=1,
            event=2,
            event_type=event_type,
            academy=2,
            cohort=(2, cohort),
            cohort_user=1,
            syllabus=2,
            syllabus_version=1,
            event_type_visibility_setting=event_type_visibility_setting,
        )
        self.client.force_authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__syllabus_visible(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": 1,
                },
                {"academy_id": 1, "allow_shared_creation": False, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": 2,
                },
                {"academy_id": 3, "allow_shared_creation": True, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=2,
                event_kwargs={"status": "ACTIVE"},
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                syllabus=1,
                syllabus_version=1,
                profile=1,
                profile_translation=2,
                event_type_visibility_setting=event_type_visibility_setting,
            )

            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            ordered_events = sorted(model.event, key=extract_starting_at)
            expected = [
                get_serializer(
                    self,
                    event,
                    model.event_type,
                    model.user,
                    model.academy[0],
                    model.city,
                    profile=model.profile,
                    profile_translations=model.profile_translation,
                )
                for event in reversed(model.event)
            ]
            expected = sorted(expected, key=lambda d: d["starting_at"])

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_one_item__status_not_active(self):
        cases = [
            (
                {
                    "academy_id": 1,
                    "cohort_id": None,
                    "syllabus_id": 1,
                },
                {"academy_id": 1, "allow_shared_creation": False, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 1,
                },
            ),
            (
                {
                    "academy_id": 4,
                    "cohort_id": None,
                    "syllabus_id": 2,
                },
                {"academy_id": 3, "allow_shared_creation": True, "icon_url": "https://www.google.com"},
                {
                    "academy_id": 4,
                },
            ),
        ]
        self.headers(academy=1)
        url = reverse_lazy("events:me")
        for event_type_visibility_setting, event_type, cohort in cases:
            model = self.bc.database.create(
                user=1,
                event=2,
                event_type=event_type,
                academy=2,
                cohort=cohort,
                cohort_user=1,
                syllabus=1,
                syllabus_version=1,
                event_type_visibility_setting=event_type_visibility_setting,
            )

            self.client.force_authenticate(model.user)

            response = self.client.get(url)
            json = response.json()
            expected = []

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, 200)
