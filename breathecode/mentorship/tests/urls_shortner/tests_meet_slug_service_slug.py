"""
Test cases for /academy/:id/member/:id
"""

import random
import urllib.parse
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
import timeago
from capyc.core.managers import feature
from django.core.handlers.wsgi import WSGIRequest
from django.template import loader
from django.test.client import FakePayload
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.mentorship.exceptions import ExtendSessionException
from breathecode.mentorship.models import MentorshipSession
from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.tests.mocks.requests import apply_requests_request_mock

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()
URL = "https://netscape.bankruptcy.story"
ROOM_NAME = "carlos-two"
ROOM_URL = ""
API_KEY = random.randint(1, 1000000000)


@pytest.fixture(autouse=True)
def setup(db, fake, monkeypatch: pytest.MonkeyPatch):
    # os.environ['APP_URL'] = fake.url()
    monkeypatch.setenv("APP_URL", fake.url())

    yield


def format_consumable(data={}):
    return {
        "cohort_set_id": None,
        "event_type_set_id": None,
        "how_many": 0,
        "id": 0,
        "mentorship_service_set_id": 0,
        "service_item_id": 0,
        "unit_type": "UNIT",
        "user_id": 0,
        "valid_until": None,
        "sort_priority": 1,
        **data,
    }


def format_consumption_session(mentorship_service, mentor_profile, mentorship_service_set, user, consumable, data={}):
    return {
        "consumable_id": consumable.id,
        "duration": timedelta(),
        "eta": ...,
        "how_many": 1.0,
        "id": 0,
        "operation_code": "default",
        "path": "payments.MentorshipServiceSet",
        "related_id": mentorship_service_set.id,
        "related_slug": mentorship_service_set.slug,
        "request": {
            "args": [],
            "headers": {"academy": None},
            "kwargs": {
                "mentor_slug": mentor_profile.slug,
                "service_slug": mentorship_service.slug,
            },
            "user": user.id,
        },
        "status": "PENDING",
        "user_id": user.id,
        "was_discounted": False,
        **data,
    }


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


def render_message(message, data={}, academy=None):
    request = None
    context = {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None, **data}

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            context["heading"] = academy.name

    return loader.render_to_string("message.html", context, request)


def get_empty_mentorship_session_queryset(*args, **kwargs):
    return MentorshipSession.objects.filter(id=0)


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def render(
    message,
    mentor_profile=None,
    token=None,
    mentorship_session=None,
    mentorship_service=None,
    fix_logo=False,
    start_session=False,
    session_expired=False,
    academy=None,
    data={},
):
    mentor_profile_slug = mentor_profile.slug if mentor_profile else "asd"
    mentorship_service_slug = mentorship_service.slug if mentorship_service else "asd"
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/{mentor_profile_slug}/service/{mentorship_service_slug}",
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": "GET",
        "SCRIPT_NAME": "",
        "SERVER_NAME": "testserver",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": FakePayload(b""),
        "wsgi.errors": None,
        "wsgi.multiprocess": True,
        "wsgi.multithread": False,
        "wsgi.run_once": False,
        "QUERY_STRING": f'token={token and token.key or ""}',
        "CONTENT_TYPE": "application/octet-stream",
    }
    request = WSGIRequest(environ)

    context = {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None, **data}

    if start_session:
        context = {
            **context,
            "SUBJECT": "Mentoring Session",
            "BUTTON": "Start Session",
            "BUTTON_TARGET": "_self",
            "LINK": f"?token={token.key}&redirect=true",
        }

    if session_expired:
        context = {
            **context,
            "BUTTON": "End Session",
            "BUTTON_TARGET": "_self",
            "LINK": f"/mentor/session/{mentorship_session.id}?token={token.key}&extend=true",
        }

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in context:
            context["heading"] = academy.name

    string = loader.render_to_string(
        "message.html",
        context,
        request,
        using=None,
    )

    if fix_logo:
        string = string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    if session_expired:
        string = string.replace("&amp;extend=true", "")

    return string


def mentor_serializer(mentor_profile, user, academy):
    return {
        "id": mentor_profile.id,
        "slug": mentor_profile.slug,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        "service": {
            "id": 1,
            "slug": "everybody-small",
            "name": "Savannah Holden DDS",
            "status": "DRAFT",
            "academy": {
                "id": academy.id,
                "slug": academy.slug,
                "name": academy.name,
                "logo_url": academy.logo_url,
                "icon_url": academy.icon_url,
            },
            "logo_url": None,
            "duration": timedelta(seconds=3600),
            "language": "en",
            "allow_mentee_to_extend": True,
            "allow_mentors_to_extend": True,
            "max_duration": timedelta(seconds=7200),
            "missed_meeting_duration": timedelta(seconds=600),
            "created_at": ...,
            "updated_at": ...,
            "description": None,
        },
        "status": mentor_profile.status,
        "price_per_hour": mentor_profile.price_per_hour,
        "booking_url": mentor_profile.booking_url,
        "online_meeting_url": mentor_profile.online_meeting_url,
        "timezone": mentor_profile.timezone,
        "syllabus": mentor_profile.syllabus,
        "email": mentor_profile.email,
        "created_at": mentor_profile.created_at,
        "updated_at": mentor_profile.updated_at,
    }


def session_serializer(mentor_profile, user, academy, mentorship_service):
    return [
        {
            "id": academy.id,
            "status": "PENDING",
            "started_at": None,
            "ended_at": None,
            "starts_at": None,
            "ends_at": ...,
            "mentor_joined_at": None,
            "mentor_left_at": None,
            "mentee_left_at": None,
            "allow_billing": True,
            "accounted_duration": None,
            "suggested_accounted_duration": None,
            "mentor": {
                "id": mentor_profile.id,
                "slug": mentor_profile.id,
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                },
                "service": {
                    "id": mentorship_service.id,
                    "slug": mentorship_service.slug,
                    "name": mentorship_service.name,
                    "status": mentorship_service.status,
                    "academy": {
                        "id": academy.id,
                        "slug": academy.slug,
                        "name": academy.name,
                        "logo_url": academy.logo_url,
                        "icon_url": academy.icon_url,
                    },
                    "logo_url": mentorship_service.logo_url,
                    "duration": mentorship_service.duration,
                    "language": mentorship_service.language,
                    "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
                    "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
                    "max_duration": mentorship_service.max_duration,
                    "missed_meeting_duration": mentorship_service.missed_meeting_duration,
                    "created_at": mentorship_service.created_at,
                    "updated_at": mentorship_service.updated_at,
                    "description": mentorship_service.description,
                },
                "status": mentor_profile.status,
                "price_per_hour": mentor_profile.price_per_hour,
                "booking_url": mentor_profile.booking_url,
                "online_meeting_url": mentor_profile.online_meeting_url,
                "timezone": mentor_profile.timezone,
                "syllabus": mentor_profile.syllabus,
                "email": mentor_profile.email,
                "created_at": mentor_profile.created_at,
                "updated_at": mentor_profile.updated_at,
            },
            "mentee": None,
        }
    ]


def render_pick_session(mentor_profile, user, token, academy, mentorship_service, fix_logo=False):
    request = None
    base_url = f"/mentor/meet/{mentor_profile.slug}/service/{mentorship_service.slug}?token={token.key}"
    booking_url = mentor_profile.booking_url
    if not booking_url.endswith("?"):
        booking_url += "?"

    context = {
        "token": token.key,
        "mentor": mentor_serializer(mentor_profile, user, academy),
        "SUBJECT": "Mentoring Session",
        "sessions": session_serializer(mentor_profile, user, academy, mentorship_service),
        "baseUrl": base_url,
    }

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in context:
            context["heading"] = academy.name

    string = loader.render_to_string("pick_session.html", context, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def render_pick_mentee(mentor_profile, user, token, academy, mentorship_service, fix_logo=False):
    request = None
    base_url = (
        f"/mentor/meet/{mentor_profile.slug}/service/{mentorship_service.slug}?token={token.key}&session={academy.id}"
    )
    booking_url = mentor_profile.booking_url
    if not booking_url.endswith("?"):
        booking_url += "?"

    context = {
        "token": token.key,
        "mentor": mentor_serializer(mentor_profile, user, academy),
        "SUBJECT": "Mentoring Session",
        "sessions": session_serializer(mentor_profile, user, academy, mentorship_service),
        "baseUrl": base_url,
    }

    string = loader.render_to_string("pick_mentee.html", context, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def get_mentorship_session_serializer(mentorship_session, mentor_profile, user, mentorship_service, academy):
    return {
        "id": mentorship_session.id,
        "status": mentorship_session.status,
        "started_at": mentorship_session.started_at,
        "ended_at": mentorship_session.ended_at,
        "starts_at": mentorship_session.starts_at,
        "ends_at": mentorship_session.ends_at,
        "mentor_joined_at": mentorship_session.mentor_joined_at,
        "mentor_left_at": mentorship_session.mentor_left_at,
        "mentee_left_at": mentorship_session.mentee_left_at,
        "allow_billing": mentorship_session.allow_billing,
        "accounted_duration": mentorship_session.accounted_duration,
        "suggested_accounted_duration": mentorship_session.suggested_accounted_duration,
        "mentor": {
            "id": mentor_profile.id,
            "slug": mentor_profile.slug,
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
            "service": {
                "id": mentorship_service.id,
                "slug": mentorship_service.slug,
                "name": mentorship_service.name,
                "status": mentorship_service.status,
                "academy": {
                    "id": academy.id,
                    "slug": academy.slug,
                    "name": academy.name,
                    "logo_url": academy.logo_url,
                    "icon_url": academy.icon_url,
                },
                "logo_url": mentorship_service.logo_url,
                "duration": mentorship_service.duration,
                "language": mentorship_service.language,
                "allow_mentee_to_extend": mentorship_service.allow_mentee_to_extend,
                "allow_mentors_to_extend": mentorship_service.allow_mentors_to_extend,
                "max_duration": mentorship_service.max_duration,
                "missed_meeting_duration": mentorship_service.missed_meeting_duration,
                "created_at": mentorship_service.created_at,
                "updated_at": mentorship_service.updated_at,
                "description": mentorship_service.description,
            },
            "status": mentor_profile.status,
            "price_per_hour": mentor_profile.price_per_hour,
            "booking_url": mentor_profile.booking_url,
            "online_meeting_url": mentor_profile.online_meeting_url,
            "timezone": mentor_profile.timezone,
            "syllabus": [],
            "email": mentor_profile.email,
            "created_at": mentor_profile.created_at,
            "updated_at": mentor_profile.updated_at,
        },
        "mentee": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
    }


def render_session(mentorship_session, mentor_profile, user, mentorship_service, academy, token, fix_logo=False):
    request = None

    data = {
        "subject": mentorship_session.service.name,
        "room_url": mentorship_session.online_meeting_url,
        "session": get_mentorship_session_serializer(
            mentorship_session, mentor_profile, user, mentorship_service, academy
        ),
        "userName": (token.user.first_name + " " + token.user.last_name).strip(),
        "backup_room_url": mentorship_session.mentor.online_meeting_url,
    }

    if token.user.id == mentorship_session.mentor.user.id:
        data["leave_url"] = "/mentor/session/" + str(mentorship_session.id) + "?token=" + token.key
    else:
        data["leave_url"] = "close"

    string = loader.render_to_string("daily.html", data, request)

    if fix_logo:
        string = string.replace('src="/static/icons/picture.png"', 'src="/static/assets/icon.png"')

    return string


class AuthenticateTestSuite(MentorshipTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy(
            "mentorship_shortner:meet_slug_service_slug", kwargs={"mentor_slug": "asd", "service_slug": "asd"}
        )
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/mentor/meet/asd/service/asd")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_without_mentor_profile(self):
        service = {"consumer": "JOIN_MENTORSHIP"}
        model = self.bc.database.create(user=1, token=1, service=service)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug_service_slug", kwargs={"mentor_slug": "asd", "service_slug": "asd"}
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f"No mentor found with slug asd")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_no_mentorship_service(self):
        slug = self.bc.fake.slug()
        service = {"consumer": "JOIN_MENTORSHIP"}
        model = self.bc.database.create(user=1, token=1, mentor_profile=1, service=service)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug_service_slug",
                kwargs={
                    "mentor_slug": model.mentor_profile.slug,
                    "service_slug": slug,
                },
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f"No service found with slug {slug}", model.mentor_profile, model.token, fix_logo=False)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_with_mentor_profile(self):
        service = {"consumer": "JOIN_MENTORSHIP"}
        model = self.bc.database.create(
            user=1,
            token=1,
            mentor_profile=1,
            mentorship_service={"language": "en", "video_provider": "DAILY"},
            service=service,
        )

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug_service_slug",
                kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(
            f"This mentor is not active at the moment",
            model.mentor_profile,
            model.token,
            fix_logo=True,
            academy=model.academy,
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorProfile"),
            [
                self.bc.format.to_dict(model.mentor_profile),
            ],
        )
        self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
        self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

    """
    🔽🔽🔽 GET without MentorProfile, bad statuses
    """

    def test_with_mentor_profile__bad_statuses(self):
        cases = [{"status": x} for x in ["INVITED", "INNACTIVE"]]

        for mentor_profile in cases:
            service = {"consumer": "JOIN_MENTORSHIP"}
            model = self.bc.database.create(
                user=1,
                token=1,
                mentor_profile=mentor_profile,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=service,
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"This mentor is not active at the moment",
                model.mentor_profile,
                model.token,
                fix_logo=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses without mentor urls
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception()))
    def test_with_mentor_profile__good_statuses__without_mentor_urls(self):
        cases = [{"status": x} for x in ["ACTIVE", "UNLISTED"]]

        for mentor_profile in cases:
            service = {"consumer": "JOIN_MENTORSHIP"}
            model = self.bc.database.create(
                user=1,
                token=1,
                mentor_profile=mentor_profile,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=service,
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"This mentor is not ready, please contact the mentor directly or anyone from the academy " "staff.",
                model.mentor_profile,
                model.token,
                fix_logo=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, with mentee
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__good_statuses__with_mentor_urls__with_mentee(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        for mentor_profile in cases:
            service = {"consumer": "JOIN_MENTORSHIP"}
            model = self.bc.database.create(
                user=1,
                token=1,
                mentor_profile=mentor_profile,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=service,
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_session(
                model.mentor_profile, model.user, model.token, model.academy, model.mentorship_service, fix_logo=True
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, with mentee of other user
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__good_statuses__with_mentor_urls__with_mentee__not_the_same_user(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        user = self.bc.database.create(user=1).user

        id = 0
        for args in cases:
            id += 1

            mentor_profile = {**args, "user_id": 1}
            service = {"consumer": "JOIN_MENTORSHIP"}
            model = self.bc.database.create(
                user=1,
                token=1,
                mentor_profile=mentor_profile,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=service,
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"Hello {model.user.first_name} {model.user.last_name}, you are about to start a "
                f"{model.mentorship_service.name} with {user.first_name} {user.last_name}.",
                model.mentor_profile,
                model.token,
                fix_logo=True,
                start_session=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without_mentee__passing_session(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        service = {"consumer": "JOIN_MENTORSHIP", "video_provider": "DAILY"}
        base = self.bc.database.create(user=1, token=1, service=service)

        id = 0
        for mentor_profile in cases:
            id += 1

            mentorship_session = {"mentee_id": None}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                mentorship_service={"video_provider": "DAILY"},
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                    "session": model.mentorship_session.id,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_mentee(
                model.mentor_profile, base.user, base.token, model.academy, model.mentorship_service, fix_logo=True
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without__passing_session__passing_mentee_does_not_exits(
        self,
    ):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        service = {"consumer": "JOIN_MENTORSHIP"}
        base = self.bc.database.create(user=1, token=1, service=service)

        id = 0
        for mentor_profile in cases:
            id += 1

            mentorship_session = {"mentee_id": None}
            model = self.bc.database.create(
                mentor_profile=mentor_profile, mentorship_session=mentorship_session, mentorship_service=1
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                    "session": model.mentorship_session.id,
                    "mentee": 10,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (
                f"/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?"
                f"token={base.token.key}&session={model.academy.id}&mentee=10"
            )
            expected = render(
                f'Mentee with user id 10 was not found, <a href="{url}&mentee=undefined">click '
                "here to start the session anyway.</a>",
                model.mentor_profile,
                base.token,
                fix_logo=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee, MentorshipSession with bad status
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__good_statuses__with_mentor_urls__session_without__passing_session__passing_mentee__bad_status(
        self,
    ):
        mentor_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        base = self.bc.database.create(user=1, token=1)

        id = 0
        for mentor_profile in mentor_cases:
            id += 1

            session_cases = [
                {
                    "status": x,
                    "mentee_id": None,
                }
                for x in ["COMPLETED", "FAILED", "IGNORED"]
            ]

            for mentorship_session in session_cases:
                service = {"consumer": "JOIN_MENTORSHIP", "video_provider": "DAILY"}
                base = self.bc.database.create(user=1, token=1, service=service)

                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    mentorship_service={"video_provider": "DAILY"},
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                querystring = self.bc.format.to_querystring(
                    {
                        "token": base.token.key,
                        "session": model.mentorship_session.id,
                        "mentee": base.user.id,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (
                    f"/mentor/meet/{model.mentor_profile.slug}?token={base.token.key}&session="
                    f"{model.academy.id}&mentee=10"
                )
                expected = render(
                    f"This mentoring session has ended ({model.mentorship_session.status}), would you like "
                    f'<a href="/mentor/meet/{model.mentor_profile.slug}">to start a new one?</a>.',
                    model.mentor_profile,
                    base.token,
                    fix_logo=True,
                    academy=model.academy,
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")
                self.bc.database.delete("auth.Permission")
                self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__passing_session__passing_mentee__passing_redirect(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in cases:
            id += 1

            service = {"consumer": "JOIN_MENTORSHIP", "video_provider": "DAILY"}
            base = self.bc.database.create(user=1, token=1, service=service)

            mentorship_session = {"mentee_id": None}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                mentorship_service={"video_provider": "DAILY"},
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                    "session": model.mentorship_session.id,
                    "mentee": base.user.id,
                    "redirect": "true",
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_session(
                model.mentorship_session,
                model.mentor_profile,
                base.user,
                model.mentorship_service,
                model.academy,
                base.token,
                fix_logo=True,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 Google Meet
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_ask_for_crendentials(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, service=service)

            mentorship_session = {"mentee_id": None, "online_meeting_url": "https://meet.google.com/abc123"}
            academy = {"available_as_saas": False}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"language": "en", "video_provider": "GOOGLE_MEET"},
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_302_FOUND)

            encoded_path = urllib.parse.urlencode({"url": url})
            Token = self.bc.database.get_model("authenticate.Token")
            token = Token.objects.filter(user=base.user).last()
            ask_for_url = reverse_lazy("auth:google_token", kwargs={"token": token.key}) + "?" + encoded_path
            self.assertEqual(response.url, ask_for_url)

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_google_meet_redirect(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, service=service, credentials_google=1)

            mentorship_session = {"mentee_id": None, "online_meeting_url": "https://meet.google.com/abc123"}
            academy = {"available_as_saas": False}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                credentials_google=1,
                mentorship_service={"language": "en", "video_provider": "GOOGLE_MEET"},
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(response.url, model.mentorship_session.online_meeting_url)

            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, user without name
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__without_user_name(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, service=service)

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": False}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"Hello student, you are about to start a {model.mentorship_service.name} with a mentor.",
                model.mentor_profile,
                base.token,
                fix_logo=True,
                start_session=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, user without name
    """

    @patch(
        "breathecode.mentorship.actions.get_pending_sessions_or_create",
        MagicMock(side_effect=Exception("Error inside get_pending_sessions_or_create")),
    )
    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_error_inside_get_pending_sessions_or_create(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        permission = {"codename": "join_mentorship"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, group=1, permission=permission)

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": False}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_message("Error inside get_pending_sessions_or_create", academy=model.academy)

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__academy_available_as_saas__flag_eq_true__mentee_with_no_consumables(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, service=service)

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": True}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            template_data = {}

            template_data["GO_BACK"] = "Go back to Dashboard"
            template_data["URL_BACK"] = "https://4geeks.com/choose-program"
            template_data["BUTTON"] = "Get a plan"
            template_data["LINK"] = f"https://4geeks.com/checkout?plan=basic&token={base.token.key}"
            expected = render("You must get a plan in order to access this service", data=template_data, academy=None)

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    def test_with_mentor_profile__academy_available_as_saas__flag_eq_true__mentee_with_no_consumables_with_subcription(
        self,
    ):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            base = self.bc.database.create(user=user, token=1, service=service, mentorship_service_set=1)

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": True}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                academy=academy,
                plan={"is_renewable": False, "mentorship_service_set": base.mentorship_service_set},
                service=1,
                subscription={"user": base.user, "selected_mentorship_service_set": base.mentorship_service_set},
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()
            model.subscription.selected_mentorship_service_set.mentorship_services.add(model.mentorship_service)
            model.subscription.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            template_data = {}

            template_data["GO_BACK"] = "Go back to Dashboard"
            template_data["URL_BACK"] = "https://4geeks.com/choose-program"
            template_data["BUTTON"] = "Get more consumables"
            template_data["LINK"] = (
                f"https://4geeks.com/checkout/mentorship/{base.mentorship_service_set.slug}?token={base.token.key}"
            )
            expected = render("with-consumer-not-enough-consumables", data=template_data, academy=None)

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_mentor_profile__academy_available_as_saas__flag_eq_true__mentee_with_consumables(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": True}
            how_many = random.randint(1, 100)
            consumable = {"how_many": how_many}
            delta = timedelta(seconds=random.randint(1, 1000))
            mentorship_service = {"max_duration": delta, "language": "en", "video_provider": "DAILY"}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service=mentorship_service,
                mentorship_service_set=1,
                academy=academy,
            )

            base = self.bc.database.create(
                user=user,
                token=1,
                service=service,
                mentorship_service=model.mentorship_service,
                mentorship_service_set=1,
                consumable=consumable,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"Hello student, you are about to start a {model.mentorship_service.name} with a mentor.",
                model.mentor_profile,
                base.token,
                fix_logo=True,
                start_session=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(
                self.bc.database.list_of("payments.Consumable"),
                [
                    format_consumable(
                        {
                            "id": base.user.id // 2,
                            "user_id": base.user.id,
                            "how_many": how_many,  # this has not discounted yet
                            "mentorship_service_set_id": base.mentorship_service_set.id,
                            "service_item_id": base.consumable.id,
                        }
                    )
                ],
            )
            self.assertEqual(
                self.bc.database.list_of("payments.ConsumptionSession"),
                [
                    format_consumption_session(
                        model.mentorship_service,
                        model.mentor_profile,
                        base.mentorship_service_set,
                        base.user,
                        base.consumable,
                        data={
                            "id": base.user.id // 2,
                            "duration": delta,
                            "eta": UTC_NOW + delta,
                        },
                    ),
                ],
            )

            self.bc.check.calls(
                tasks.end_the_consumption_session.apply_async.call_args_list,
                [
                    call(args=(id, 1), eta=UTC_NOW + delta),
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")
            tasks.end_the_consumption_session.apply_async.call_args_list = []

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__academy_available_as_saas__flag_eq_true__bypass_mentor_consume(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]
        service = {"consumer": "JOIN_MENTORSHIP"}

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}

            mentorship_session = {"mentee_id": None}
            academy = {"available_as_saas": True}
            delta = timedelta(seconds=random.randint(1, 1000))
            mentorship_service = {"max_duration": delta, "language": "en"}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                token=1,
                service=service,
                mentorship_service=mentorship_service,
                mentorship_service_set=1,
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": model.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_session(
                model.mentor_profile, model.user, model.token, model.academy, model.mentorship_service, fix_logo=True
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("auth.User")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, with ends_at
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=10)
            mentorship_session = {"mentee_id": None, "ends_at": ends_at}
            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                mentorship_service={"video_provider": "DAILY"},
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            querystring = self.bc.format.to_querystring(
                {
                    "token": base.token.key,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (
                f"/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?"
                f"token={base.token.key}&extend=true"
            )
            expected = render(
                f'The mentoring session expired {timeago.format(ends_at, UTC_NOW)}: You can <a href="{url}">'
                "extend it for another 30 minutes</a> or end the session right now.",
                model.mentor_profile,
                base.token,
                mentorship_session=model.mentorship_session,
                fix_logo=True,
                session_expired=True,
                academy=model.academy,
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls, MentorshipSession without mentee
    passing session and mentee but mentee does not exist, with ends_at, with extend true
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.extend_session", MagicMock(side_effect=lambda x: x))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session_base = {"mentee_id": base.user.id, "ends_at": ends_at}
            # session, token
            cases = [
                (
                    {
                        **mentorship_session_base,
                        "allow_mentee_to_extend": True,
                        "allow_mentors_to_extend": False,
                    },
                    None,
                ),
                (
                    {
                        **mentorship_session_base,
                        "allow_mentee_to_extend": False,
                        "allow_mentors_to_extend": True,
                    },
                    1,
                ),
            ]

            for mentorship_session, token in cases:
                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    user=user,
                    token=token,
                    mentorship_service={"language": "en", "video_provider": "DAILY"},
                    service=base.service,
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if "token" in model else base.token

                querystring = self.bc.format.to_querystring(
                    {
                        "token": token.key,
                        "extend": "true",
                        "mentee": base.user.id,
                        "session": model.mentorship_session.id,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)

                url = (
                    f"/mentor/meet/{model.mentor_profile.slug}/service/{model.mentorship_service.slug}?"
                    f"token={token.key}&extend=true&mentee={base.user.id}&session={model.mentorship_session.id}"
                )
                expected = render(
                    f"The mentoring session expired {timeago.format(ends_at, UTC_NOW)}: You can "
                    f'<a href="{url}">extend it for another 30 minutes</a> or end the session right now.',
                    model.mentor_profile,
                    token,
                    mentorship_session=model.mentorship_session,
                    fix_logo=True,
                    session_expired=True,
                    academy=model.academy,
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.mentorship.actions.extend_session", MagicMock(side_effect=ExtendSessionException("xyz")))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__extend_session_raise_exception(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session = {"mentee_id": base.user.id, "ends_at": ends_at}
            # session, token
            cases = [
                (
                    {
                        "allow_mentors_to_extend": True,
                        "allow_mentee_to_extend": False,
                        "language": "en",
                        "video_provider": "DAILY",
                    },
                    1,
                ),
                (
                    {
                        "allow_mentee_to_extend": False,
                        "allow_mentee_to_extend": True,
                        "language": "en",
                        "video_provider": "DAILY",
                    },
                    None,
                ),
            ]

            for mentorship_service, token in cases:
                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    user=user,
                    token=token,
                    mentorship_service=mentorship_service,
                    service=base.service,
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if "token" in model else base.token

                querystring = self.bc.format.to_querystring(
                    {
                        "token": token.key,
                        "extend": "true",
                        "mentee": base.user.id,
                        "session": model.mentorship_session.id,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (
                    f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
                    f"mentee={base.user.id}&session={model.mentorship_session.id}"
                )
                expected = render(
                    "xyz",
                    model.mentor_profile,
                    token,
                    mentorship_session=model.mentorship_session,
                    fix_logo=True,
                    session_expired=True,
                    academy=model.academy,
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception,
    session can't be extended
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__session_can_not_be_extended(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=10)

            mentorship_session = {"mentee_id": base.user.id, "ends_at": ends_at}
            # service, token
            cases = [
                (
                    {
                        "allow_mentors_to_extend": False,
                        "allow_mentee_to_extend": False,
                        "language": "en",
                        "video_provider": "DAILY",
                    },
                    None,
                ),
                (
                    {
                        "allow_mentors_to_extend": False,
                        "allow_mentee_to_extend": False,
                        "language": "en",
                        "video_provider": "DAILY",
                    },
                    1,
                ),
            ]

            for mentorship_service, token in cases:
                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    user=user,
                    token=token,
                    mentorship_service=mentorship_service,
                    service=base.service,
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if "token" in model else base.token

                querystring = self.bc.format.to_querystring(
                    {
                        "token": token.key,
                        "extend": "true",
                        "mentee": base.user.id,
                        "session": model.mentorship_session.id,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (
                    f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
                    f"mentee={base.user.id}&session={model.mentorship_session.id}"
                )
                expected = render(
                    "The mentoring session expired 10 seconds ago and it cannot be extended.",
                    model.mentor_profile,
                    token,
                    mentorship_session=model.mentorship_session,
                    fix_logo=True,
                    academy=model.academy,
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")

            # teardown
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception, redirect
    to session
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__ends_at_less_now__with_extend_true__redirect_to_session(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            mentorship_session_base = {"mentee_id": base.user.id, "ends_at": ends_at}
            # session, token
            cases = [
                (
                    {
                        **mentorship_session_base,
                        "allow_mentors_to_extend": True,
                    },
                    None,
                ),
                (
                    {
                        **mentorship_session_base,
                        "allow_mentee_to_extend": True,
                    },
                    1,
                ),
            ]

            for mentorship_session, token in cases:
                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    user=user,
                    token=token,
                    mentorship_service={"language": "en", "video_provider": "DAILY"},
                    service=base.service,
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                token = model.token if "token" in model else base.token

                querystring = self.bc.format.to_querystring(
                    {
                        "token": token.key,
                        "extend": "true",
                        "mentee": base.user.id,
                        "session": model.mentorship_session.id,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = (
                    f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
                    f"mentee={base.user.id}&session={model.mentorship_session.id}"
                )
                expected = ""

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
                minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
                message = (
                    f"You have a session that expired {expired_at}. Only sessions with less than "
                    f"{minutes}min from expiration can be extended (if allowed by the academy)"
                ).replace(" ", "%20")
                self.assertEqual(
                    response.url,
                    f"/mentor/session/{model.mentorship_session.id}?token=" f"{token.key}&message={message}",
                )
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception, redirect
    to session, no saas
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_with_mentor_profile__redirect_to_session__no_saas(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            mentorship_session_base = {"mentee_id": base.user.id, "ends_at": ends_at}
            mentorship_session = {
                **mentorship_session_base,
                "allow_mentee_to_extend": True,
            }
            token = 1

            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                token=token,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=base.service,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            token = model.token if "token" in model else base.token

            querystring = self.bc.format.to_querystring(
                {
                    "token": token.key,
                    "extend": "true",
                    "mentee": base.user.id,
                    "session": model.mentorship_session.id,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (
                f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
                f"mentee={base.user.id}&session={model.mentorship_session.id}"
            )
            expected = ""

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
            minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
            message = (
                f"You have a session that expired {expired_at}. Only sessions with less than "
                f"{minutes}min from expiration can be extended (if allowed by the academy)"
            ).replace(" ", "%20")
            self.assertEqual(
                response.url, f"/mentor/session/{model.mentorship_session.id}?token=" f"{token.key}&message={message}"
            )
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET without MentorProfile, with ends_at, with extend true, extend_session raise exception, redirect
    to session, saas
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("capyc.core.managers.feature.is_enabled", MagicMock(return_value=False))
    def test_with_mentor_profile__redirect_to_session__saas__bypass_consumption_false(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            academy = {"available_as_saas": True}
            mentorship_session = {
                "mentee_id": base.user.id,
                "ends_at": ends_at,
                "allow_mentee_to_extend": True,
            }
            token = 1

            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                token=token,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=base.service,
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            token = model.token if "token" in model else base.token

            querystring = self.bc.format.to_querystring(
                {
                    "token": token.key,
                    "extend": "true",
                    "mentee": base.user.id,
                    "session": model.mentorship_session.id,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render("mentee-not-enough-consumables")

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
            calls = [
                call(
                    args[0],
                    {
                        **args[1],
                        "context": {
                            **args[1]["context"],
                            "request": type(args[1]["context"]["request"]),
                            "consumer": callable(args[1]["context"]["consumer"]),
                            "consumables": [x for x in args[1]["context"]["consumables"]],
                        },
                    },
                    *args[2:],
                    **kwargs,
                )
                for args, kwargs in feature.is_enabled.call_args_list
            ]
            context1 = feature.context(
                context={
                    "utc_now": UTC_NOW,
                    "consumer": True,
                    "service": "join_mentorship",
                    "request": WSGIRequest,
                    "consumables": [],
                    "lifetime": None,
                    "price": 0,
                    "is_consumption_session": False,
                    "flags": {"bypass_consumption": False},
                },
                kwargs={
                    "token": model.token,
                    "mentor_profile": model.mentor_profile,
                    "mentorship_service": model.mentorship_service,
                },
            )
            context2 = feature.context(
                context={
                    "utc_now": UTC_NOW,
                    "consumer": True,
                    "service": "join_mentorship",
                    "request": WSGIRequest,
                    "consumables": [],
                    "lifetime": None,
                    "price": 0,
                    "is_consumption_session": False,
                    "flags": {"bypass_consumption": False},
                },
                kwargs={
                    "token": model.token,
                    "mentor_profile": model.mentor_profile,
                    "mentorship_service": model.mentorship_service,
                },
                user=base.user,
            )
            assert calls == [
                call("payments.bypass_consumption", context1, False),
                call("payments.bypass_consumption", context2, False),
            ]

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")
            feature.is_enabled.call_args_list = []

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("capyc.core.managers.feature.is_enabled", MagicMock(side_effect=[False, True, False, True]))
    def test_with_mentor_profile__redirect_to_session__saas__bypass_consumption_true(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            base = self.bc.database.create(user=user, token=1, service=service)

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            academy = {"available_as_saas": True}
            mentorship_session = {
                "mentee_id": base.user.id,
                "ends_at": ends_at,
                "allow_mentee_to_extend": True,
            }
            token = 1

            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                token=token,
                mentorship_service={"language": "en", "video_provider": "DAILY"},
                service=base.service,
                academy=academy,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            token = model.token if "token" in model else base.token

            querystring = self.bc.format.to_querystring(
                {
                    "token": token.key,
                    "extend": "true",
                    "mentee": base.user.id,
                    "session": model.mentorship_session.id,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = ""

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            assert (
                response.url
                == f"/mentor/session/{model.mentorship_session.id}?token={token.key}&message=You%20have%20a%20session%20that%20expired%2030%20minutes%20ago.%20Only%20sessions%20with%20less%20than%2030min%20from%20expiration%20can%20be%20extended%20(if%20allowed%20by%20the%20academy)"
            )
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )
            self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
            self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])
            calls = [
                call(
                    args[0],
                    {
                        **args[1],
                        "context": {
                            **args[1]["context"],
                            "request": type(args[1]["context"]["request"]),
                            "consumer": callable(args[1]["context"]["consumer"]),
                            "consumables": [x for x in args[1]["context"]["consumables"]],
                        },
                    },
                    *args[2:],
                    **kwargs,
                )
                for args, kwargs in feature.is_enabled.call_args_list
            ]
            context1 = feature.context(
                context={
                    "utc_now": UTC_NOW,
                    "consumer": True,
                    "service": "join_mentorship",
                    "request": WSGIRequest,
                    "consumables": [],
                    "lifetime": None,
                    "price": 0,
                    "is_consumption_session": False,
                    "flags": {"bypass_consumption": False},
                },
                kwargs={
                    "token": model.token,
                    "mentor_profile": model.mentor_profile,
                    "mentorship_service": model.mentorship_service,
                },
            )
            context2 = feature.context(
                context={
                    "utc_now": UTC_NOW,
                    "consumer": True,
                    "service": "join_mentorship",
                    "request": WSGIRequest,
                    "consumables": [],
                    "lifetime": None,
                    "price": 0,
                    "is_consumption_session": False,
                    "flags": {"bypass_consumption": False},
                },
                kwargs={
                    "token": model.token,
                    "mentor_profile": model.mentor_profile,
                    "mentorship_service": model.mentorship_service,
                },
                user=base.user,
            )
            assert calls == [
                call("payments.bypass_consumption", context1, False),
                call("payments.bypass_consumption", context2, False),
            ]

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.Service")
            feature.is_enabled.call_args_list = []

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.payments.tasks.end_the_consumption_session.apply_async", MagicMock(return_value=None))
    def test_with_mentor_profile__redirect_to_session__saas__(self):
        mentor_profile_cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in mentor_profile_cases:
            id += 1

            user = {"first_name": "", "last_name": ""}
            service = {"consumer": "JOIN_MENTORSHIP"}
            academy = {"available_as_saas": True}
            how_many = random.randint(1, 100)
            consumable = {"how_many": how_many}

            delta = timedelta(seconds=random.randint(1, 1000))
            mentorship_service = {"max_duration": delta, "language": "en", "video_provider": "DAILY"}
            base = self.bc.database.create(
                user=user,
                token=1,
                service=service,
                consumable=consumable,
                mentorship_service=mentorship_service,
                mentorship_service_set=1,
                academy=academy,
            )

            ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

            mentorship_session = {
                "mentee_id": base.user.id,
                "ends_at": ends_at,
                "allow_mentee_to_extend": True,
            }
            token = 1

            model = self.bc.database.create(
                mentor_profile=mentor_profile,
                mentorship_session=mentorship_session,
                user=user,
                token=token,
                mentorship_service=base.mentorship_service,
                service=base.service,
            )

            model.mentorship_session.mentee = None
            model.mentorship_session.save()

            token = model.token if "token" in model else base.token

            querystring = self.bc.format.to_querystring(
                {
                    "token": token.key,
                    "extend": "true",
                    "mentee": base.user.id,
                    "session": model.mentorship_session.id,
                }
            )
            url = (
                reverse_lazy(
                    "mentorship_shortner:meet_slug_service_slug",
                    kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
                )
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            url = (
                f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
                f"mentee={base.user.id}&session={model.mentorship_session.id}"
            )
            expected = ""

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
            minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
            message = (
                f"You have a session that expired {expired_at}. Only sessions with less than "
                f"{minutes}min from expiration can be extended (if allowed by the academy)"
            ).replace(" ", "%20")
            self.assertEqual(
                response.url, f"/mentor/session/{model.mentorship_session.id}?token=" f"{token.key}&message={message}"
            )
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )

            self.assertEqual(
                self.bc.database.list_of("payments.Consumable"),
                [
                    format_consumable(
                        {
                            "id": base.user.id if base.user.id == 1 else 2,
                            "user_id": base.user.id,
                            "how_many": how_many,  # this has not discounted yet
                            "mentorship_service_set_id": base.mentorship_service_set.id,
                            "service_item_id": base.consumable.id,
                        }
                    )
                ],
            )
            self.assertEqual(
                self.bc.database.list_of("payments.ConsumptionSession"),
                [
                    format_consumption_session(
                        model.mentorship_service,
                        model.mentor_profile,
                        base.mentorship_service_set,
                        base.user,
                        base.consumable,
                        data={
                            "id": base.user.id if base.user.id == 1 else 2,
                            "duration": delta,
                            "eta": UTC_NOW + delta,
                        },
                    ),
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
            self.bc.database.delete("auth.Permission")
            self.bc.database.delete("payments.ConsumptionSession")
            self.bc.database.delete("payments.Consumable")
            self.bc.database.delete("payments.Service")

    """
    🔽🔽🔽 GET mock get_pending_sessions_or_create to get a empty queryset
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "DAILY_API_URL": URL,
                    "DAILY_API_KEY": API_KEY,
                }
            )
        ),
    )
    @patch(
        "requests.request",
        apply_requests_request_mock(
            [
                (
                    201,
                    f"{URL}/v1/rooms",
                    {
                        "name": ROOM_NAME,
                        "url": ROOM_URL,
                    },
                )
            ]
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch(
        "breathecode.mentorship.actions.get_pending_sessions_or_create",
        MagicMock(side_effect=get_empty_mentorship_session_queryset),
    )
    def test_get_pending_sessions_or_create_returns_empty_queryset(self):

        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        id = 0
        for mentor_profile in cases:
            id += 1

            first_name = self.bc.fake.first_name()
            last_name = self.bc.fake.last_name()
            cases = [
                ({"first_name": "", "last_name": ""}, "the mentor"),
                ({"first_name": first_name, "last_name": last_name}, f"{first_name} {last_name}"),
            ]

            for user, name in cases:
                service = {"consumer": "JOIN_MENTORSHIP"}
                base = self.bc.database.create(user=user, token=1, service=service)

                ends_at = UTC_NOW - timedelta(seconds=10)
                mentorship_session = {"mentee_id": None, "ends_at": ends_at}
                model = self.bc.database.create(
                    mentor_profile=mentor_profile,
                    mentorship_session=mentorship_session,
                    user=user,
                    mentorship_service=1,
                )

                model.mentorship_session.mentee = None
                model.mentorship_session.save()

                querystring = self.bc.format.to_querystring(
                    {
                        "token": base.token.key,
                    }
                )
                url = (
                    reverse_lazy(
                        "mentorship_shortner:meet_slug_service_slug",
                        kwargs={
                            "mentor_slug": model.mentor_profile.slug,
                            "service_slug": model.mentorship_service.slug,
                        },
                    )
                    + f"?{querystring}"
                )
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                url = f"/mentor/meet/{model.mentor_profile.slug}?token={base.token.key}&extend=true"
                expected = render(
                    f"Impossible to create or retrieve mentoring session with {name}.",
                    model.mentor_profile,
                    base.token,
                    mentorship_session=model.mentorship_session,
                    fix_logo=True,
                    academy=model.academy,
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    self.bc.database.list_of("mentorship.MentorProfile"),
                    [
                        self.bc.format.to_dict(model.mentor_profile),
                    ],
                )
                self.assertEqual(self.bc.database.list_of("payments.Consumable"), [])
                self.assertEqual(self.bc.database.list_of("payments.ConsumptionSession"), [])

                # teardown
                self.bc.database.delete("mentorship.MentorProfile")
                self.bc.database.delete("auth.Permission")
                self.bc.database.delete("payments.Service")


# Given: A no SAAS student who has paid
# When: auth
# Then: response 200
@pytest.mark.parametrize(
    "cohort_user",
    [
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "GRADUATED",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "GRADUATED",
        },
    ],
)
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
@patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
@patch(
    "os.getenv",
    MagicMock(
        side_effect=apply_get_env(
            {
                "DAILY_API_URL": URL,
                "DAILY_API_KEY": API_KEY,
            }
        )
    ),
)
@patch(
    "requests.request",
    apply_requests_request_mock(
        [
            (
                201,
                f"{URL}/v1/rooms",
                {
                    "name": ROOM_NAME,
                    "url": ROOM_URL,
                },
            )
        ]
    ),
)
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
@patch(
    "breathecode.mentorship.actions.get_pending_sessions_or_create",
    MagicMock(side_effect=get_empty_mentorship_session_queryset),
)
def test__post__auth__no_saas__finantial_status_no_late(
    bc: Breathecode, client: capy.Client, academy, cohort, cohort_user
):

    mentor_profile_cases = [
        {
            "status": x,
            "online_meeting_url": bc.fake.url(),
            "booking_url": bc.fake.url(),
        }
        for x in ["ACTIVE", "UNLISTED"]
    ]

    id = 0
    for mentor_profile in mentor_profile_cases:
        id += 1

        user = {"first_name": "", "last_name": ""}
        service = {"consumer": "JOIN_MENTORSHIP"}
        base = bc.database.create(
            user=user, token=1, service=service, academy=academy, cohort=cohort, cohort_user=cohort_user
        )

        ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

        mentorship_session_base = {"mentee_id": base.user.id, "ends_at": ends_at}
        mentorship_session = {
            **mentorship_session_base,
            "allow_mentee_to_extend": True,
            "name": "Session 1",
        }
        token = 1

        model = bc.database.create(
            mentor_profile=mentor_profile,
            mentorship_session=mentorship_session,
            user=user,
            token=token,
            mentorship_service={"language": "en", "video_provider": "DAILY"},
            service=base.service,
        )

        model.mentorship_session.mentee = None
        model.mentorship_session.save()

        token = base.token

        querystring = bc.format.to_querystring(
            {
                "token": token.key,
                "extend": "true",
                "mentee": base.user.id,
                "session": model.mentorship_session.id,
            }
        )
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug_service_slug",
                kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
            )
            + f"?{querystring}"
        )
        response = client.get(url)

        content = bc.format.from_bytes(response.content)
        url = (
            f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
            f"mentee={base.user.id}&session={model.mentorship_session.id}"
        )
        expected = ""

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        assert content == expected
        expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
        minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
        message = (
            f"You have a session that expired {expired_at}. Only sessions with less than "
            f"{minutes}min from expiration can be extended (if allowed by the academy)"
        ).replace(" ", "%20")
        assert response.url == f"/mentor/session/{model.mentorship_session.id}?token={token.key}&message={message}"
        assert response.status_code, status.HTTP_302_FOUND
        assert bc.database.list_of("mentorship.MentorProfile") == [
            bc.format.to_dict(model.mentor_profile),
        ]
        assert bc.database.list_of("payments.Consumable") == []
        assert bc.database.list_of("payments.ConsumptionSession") == []

        # teardown
        bc.database.delete("mentorship.MentorProfile")
        bc.database.delete("auth.Permission")
        bc.database.delete("payments.Service")


# Given: A no SAAS student who hasn't paid
# When: auth
# Then: response 402
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
@patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
@patch(
    "os.getenv",
    MagicMock(
        side_effect=apply_get_env(
            {
                "DAILY_API_URL": URL,
                "DAILY_API_KEY": API_KEY,
            }
        )
    ),
)
@patch(
    "requests.request",
    apply_requests_request_mock(
        [
            (
                201,
                f"{URL}/v1/rooms",
                {
                    "name": ROOM_NAME,
                    "url": ROOM_URL,
                },
            )
        ]
    ),
)
@patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
@patch(
    "breathecode.mentorship.actions.get_pending_sessions_or_create",
    MagicMock(side_effect=get_empty_mentorship_session_queryset),
)
def test__post__auth__no_saas__finantial_status_late(bc: Breathecode, client: capy.Client, academy, cohort):

    mentor_profile_cases = [
        {
            "status": x,
            "online_meeting_url": bc.fake.url(),
            "booking_url": bc.fake.url(),
        }
        for x in ["ACTIVE", "UNLISTED"]
    ]

    id = 0
    for mentor_profile in mentor_profile_cases:
        id += 1

        user = {"first_name": "", "last_name": ""}
        service = {"consumer": "JOIN_MENTORSHIP"}
        cohort_user = {"finantial_status": "LATE", "educational_status": "ACTIVE"}
        base = bc.database.create(
            user=user, token=1, service=service, academy=academy, cohort=cohort, cohort_user=cohort_user
        )

        ends_at = UTC_NOW - timedelta(seconds=3600 / 2 + 1)

        mentorship_session_base = {"mentee_id": base.user.id, "ends_at": ends_at}
        mentorship_session = {
            **mentorship_session_base,
            "allow_mentee_to_extend": True,
        }
        token = 1

        model = bc.database.create(
            mentor_profile=mentor_profile,
            academy=base.academy,
            mentorship_session=mentorship_session,
            user=user,
            token=token,
            mentorship_service={"language": "en", "video_provider": "DAILY"},
        )

        model.mentorship_session.mentee = None
        model.mentorship_session.save()

        token = base.token

        querystring = bc.format.to_querystring(
            {
                "token": token.key,
                "extend": "true",
                "mentee": base.user.id,
                "session": model.mentorship_session.id,
            }
        )
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug_service_slug",
                kwargs={"mentor_slug": model.mentor_profile.slug, "service_slug": model.mentorship_service.slug},
            )
            + f"?{querystring}"
        )
        response = client.get(url)

        content = bc.format.from_bytes(response.content)
        url = (
            f"/mentor/meet/{model.mentor_profile.slug}?token={token.key}&extend=true&"
            f"mentee={base.user.id}&session={model.mentorship_session.id}"
        )
        expected = render_message(
            "You must get a plan in order to access this service",
            data={
                "GO_BACK": "Go back to Dashboard",
                "URL_BACK": "https://4geeks.com/choose-program",
                "BUTTON": "Get a plan",
                "LINK": f"https://4geeks.com/checkout?plan=basic&token={base.token.key}",
            },
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        assert content == expected
        expired_at = timeago.format(model.mentorship_session.ends_at, UTC_NOW)
        minutes = round(((model.mentorship_session.service.duration.total_seconds() / 3600) * 60) / 2)
        message = (
            f"You have a session that expired {expired_at}. Only sessions with less than "
            f"{minutes}min from expiration can be extended (if allowed by the academy)"
        ).replace(" ", "%20")
        assert response.status_code, status.HTTP_402_PAYMENT_REQUIRED
        assert bc.database.list_of("mentorship.MentorProfile") == [
            bc.format.to_dict(model.mentor_profile),
        ]
        assert bc.database.list_of("payments.Consumable") == []
        assert bc.database.list_of("payments.ConsumptionSession") == []

        # teardown
        bc.database.delete("mentorship.MentorProfile")
        bc.database.delete("auth.Permission")
        bc.database.delete("payments.Service")
