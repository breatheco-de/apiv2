"""
Test cases for /academy/:id/member/:id
"""

from unittest.mock import MagicMock, patch

from django.core.handlers.wsgi import WSGIRequest
from django.template import loader
from django.test.client import FakePayload
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import MentorshipTestCase

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def render(message, mentor_profile=None, token=None, fix_logo=False, academy=None):
    slug = mentor_profile.slug if mentor_profile else "asd"
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/{slug}",
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

    data = {}

    if academy:
        data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        data["COMPANY_LOGO"] = academy.logo_url
        data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            data["heading"] = academy.name

    string = loader.render_to_string(
        "message.html",
        {
            "MESSAGE": message,
            "BUTTON": None,
            "BUTTON_TARGET": "_blank",
            "LINK": None,
            **data,
        },
        request,
        using=None,
    )

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def render_successfully(mentor_profile, user, fix_logo=False, academy=None):
    request = None
    booking_url = mentor_profile.booking_url
    if not booking_url.endswith("?"):
        booking_url += "?"

    data = {
        "SUBJECT": "Mentoring Session",
        "mentor": mentor_profile,
        "mentee": user,
        "booking_url": booking_url,
        "LOGO_IN_CONTENT": True,
    }

    if academy:
        data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        data["COMPANY_LOGO"] = academy.logo_url
        data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            data["heading"] = academy.name

    string = loader.render_to_string("book_session.html", data, request)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


class AuthenticateTestSuite(MentorshipTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": "asd"})
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/mentor/asd")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_without_mentor_profile(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": "asd"}) + f"?{querystring}"
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

    """
    🔽🔽🔽 GET without MentorProfile
    """

    def test_with_mentor_profile(self):
        model = self.bc.database.create(user=1, token=1, mentor_profile=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": model.mentor_profile.slug})
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(
            f"This mentor is not active", model.mentor_profile, model.token, fix_logo=True, academy=model.academy
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

    """
    🔽🔽🔽 GET without MentorProfile, bad statuses
    """

    def test_with_mentor_profile__bad_statuses(self):
        cases = [{"status": x} for x in ["INVITED", "INNACTIVE"]]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1, token=1, mentor_profile=mentor_profile)

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": model.mentor_profile.slug})
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"This mentor is not active", model.mentor_profile, model.token, fix_logo=True, academy=model.academy
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

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses without mentor urls
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock(side_effect=Exception()))
    def test_with_mentor_profile__good_statuses__without_mentor_urls(self):
        cases = [{"status": x} for x in ["ACTIVE", "UNLISTED"]]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1, token=1, mentor_profile=mentor_profile)

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": model.mentor_profile.slug})
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                f"This mentor is not ready, please contact the mentor directly or anyone from the academy staff.",
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
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorProfile"),
                [
                    self.bc.format.to_dict(model.mentor_profile),
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")

    """
    🔽🔽🔽 GET without MentorProfile, good statuses with mentor urls
    """

    @patch("breathecode.mentorship.actions.mentor_is_ready", MagicMock())
    def test_with_mentor_profile__good_statuses__with_mentor_urls(self):
        cases = [
            {
                "status": x,
                "online_meeting_url": self.bc.fake.url(),
                "booking_url": self.bc.fake.url(),
            }
            for x in ["ACTIVE", "UNLISTED"]
        ]

        for mentor_profile in cases:
            model = self.bc.database.create(user=1, token=1, mentor_profile=mentor_profile)

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy("mentorship_shortner:slug", kwargs={"mentor_slug": model.mentor_profile.slug})
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_successfully(model.mentor_profile, model.user, fix_logo=True, academy=model.academy)

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

            # teardown
            self.bc.database.delete("mentorship.MentorProfile")
