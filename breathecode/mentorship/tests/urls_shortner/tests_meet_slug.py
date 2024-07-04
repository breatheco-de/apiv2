"""
Test cases for /academy/:id/member/:id
"""

import random
from unittest.mock import MagicMock, patch

from django.core.handlers.wsgi import WSGIRequest
from django.template import loader
from django.test.client import FakePayload
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()
URL = "https://netscape.bankruptcy.story"
ROOM_NAME = "carlos-two"
ROOM_URL = ""
API_KEY = random.randint(1, 1000000000)


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

    context = {
        "MESSAGE": message,
        "BUTTON": None,
        "BUTTON_TARGET": "_blank",
        "LINK": None,
    }

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in context:
            context["heading"] = academy.name

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


def render_pick_service(mentor_profile, token, mentorship_services=[], fix_logo=False, academy=None):
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/meet/{mentor_profile.slug}",
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
    base_url = f"/mentor/meet/{mentor_profile.slug}"

    context = {
        "token": token.key,
        "services": mentorship_services,
        "mentor": mentor_profile,
        "baseUrl": base_url,
    }

    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in context:
            context["heading"] = academy.name

    string = loader.render_to_string("pick_service.html", context, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


class AuthenticateTestSuite(MentorshipTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy(
            "mentorship_shortner:meet_slug",
            kwargs={
                "mentor_slug": "asd",
            },
        )
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/mentor/meet/asd")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_without_mentor_profile(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug",
                kwargs={
                    "mentor_slug": "asd",
                },
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorProfile"), [])
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    """
    🔽🔽🔽 GET with MentorProfile
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception("kjhgf")))
    def test_with_mentor_profile__mentor_is_not_ready(self):
        model = self.bc.database.create(user=1, token=1, mentor_profile=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug",
                kwargs={
                    "mentor_slug": model.mentor_profile.slug,
                },
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(
            "This mentor is not ready, please contact the mentor directly or anyone from the academy staff.",
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

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test_with_mentor_profile__mentor_ready(self):
        model = self.bc.database.create(user=1, token=1, mentor_profile=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug",
                kwargs={
                    "mentor_slug": model.mentor_profile.slug,
                },
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f"This mentor is not available on any service", academy=model.academy)

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

        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipService"), [])

    """
    🔽🔽🔽 GET with MentorProfile and MentorshipService
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test_with_mentor_profile__with_mentorship_service(self):
        model = self.bc.database.create(user=1, token=1, mentor_profile=1, mentorship_service=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy(
                "mentorship_shortner:meet_slug",
                kwargs={
                    "mentor_slug": model.mentor_profile.slug,
                },
            )
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_pick_service(
            model.mentor_profile, model.token, [model.mentorship_service], academy=model.academy
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
            self.bc.database.list_of("mentorship.MentorshipService"),
            [
                self.bc.format.to_dict(model.mentorship_service),
            ],
        )
