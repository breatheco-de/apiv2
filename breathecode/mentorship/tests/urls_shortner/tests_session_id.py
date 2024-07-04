"""
Test cases for /academy/:id/member/:id
"""

from random import randint
from unittest.mock import MagicMock, call, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.handlers.wsgi import WSGIRequest
from django.http import QueryDict
from django.template import loader
from django.test.client import FakePayload
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.mentorship.forms import CloseMentoringSessionForm
from breathecode.mentorship.models import MentorshipSession
from breathecode.notify import actions
from breathecode.tests.mixins.legacy import LegacyAPITestCase

UTC_NOW = timezone.now()
CSRF_TOKEN = str(randint(10000, 10000000000000))


class Message(str):
    tags: str

    def __init__(self, css_class, *_):
        self.tags = css_class
        return super().__init__()

    def __new__(cls, _, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)


def render(message, mentorship_session=None, token=None):
    pk = mentorship_session.id if mentorship_session else 1
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/session/{pk}",
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

    string = loader.render_to_string(
        "message.html",
        {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None},
        request,
        using=None,
    )

    return string


def render_form(self, mentorship_session=None, token=None, data={}, post=False, fix_logo=False):
    mentee = mentorship_session.mentee
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/session/{mentorship_session.id}",
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

    if post:
        environ["REQUEST_METHOD"] = "POST"
        environ["CONTENT_TYPE"] = "multipart/form-data; boundary=BoUnDaRyStRiNg; charset=utf-8"

    request = WSGIRequest(environ)

    querystring = self.bc.format.to_querystring(data)
    data = QueryDict(querystring, mutable=True)
    data["token"] = token.key if token else ""

    if not post:
        data["status"] = "COMPLETED"
        data["summary"] = mentorship_session.summary

    data["session_id"] = mentorship_session.id

    if mentee and not post:
        data["student_name"] = f"{mentee.first_name} {mentee.last_name}, {mentee.email}"

    form = CloseMentoringSessionForm(data)

    string = loader.render_to_string(
        "form.html",
        {
            "form": form,
            "disabled": False,
            "btn_lable": "End Mentoring Session",
            "intro": "Please fill the following information to formally end the session",
            "title": "End Mentoring Session",
        },
        request,
        using=None,
    )

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    else:
        return string.replace('src="/static/icons/picture.png"', 'src="/static/assets/logo.png"')


def render_post_form(self, messages=[], mentorship_session=None, token=None, data={}, fix_logo=False):
    pk = mentorship_session.id if mentorship_session else 1
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/mentor/session/{pk}",
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": "POST",
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
        "CONTENT_TYPE": "multipart/form-data; boundary=BoUnDaRyStRiNg; charset=utf-8",
    }
    request = WSGIRequest(environ)

    querystring = self.bc.format.to_querystring(data)
    data = QueryDict(querystring, mutable=True)
    form = CloseMentoringSessionForm(data)

    context = {"form": form}

    if messages:
        context["messages"] = messages

    string = loader.render_to_string("form.html", context, request, using=None)

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


def mentor_profile_serializer(mentor_profile, user, mentorship_service, academy):
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
    }


def mentorship_session_serializer(mentor_profile, mentorship_service, academy, user):
    mentorship_sessions = MentorshipSession.objects.filter(
        mentor__id=mentor_profile.id, status__in=["STARTED", "PENDING"]
    )

    return [
        {
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
                "syllabus": mentor_profile.syllabus,
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
        for mentorship_session in mentorship_sessions
    ]


def render_close_session(message, mentor_profile, user, token, mentorship_service, academy, fix_logo=False):
    request = None

    context = {}
    if academy:
        context["COMPANY_INFO_EMAIL"] = academy.feedback_email
        context["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        context["COMPANY_LOGO"] = academy.logo_url
        context["COMPANY_NAME"] = academy.name

        if "heading" not in context:
            context["heading"] = academy.name

    string = loader.render_to_string(
        "close_session.html",
        {
            "token": token.key,
            "message": message,
            "mentor": mentor_profile_serializer(mentor_profile, user, mentorship_service, academy),
            "mentee": user,
            "SUBJECT": "Close Mentoring Session",
            "sessions": mentorship_session_serializer(mentor_profile, mentorship_service, academy, user),
            "baseUrl": f"/mentor/session/{mentor_profile.id}",
            **context,
        },
        request,
    )

    if fix_logo:
        return string.replace('src="/static/assets/logo.png"', 'src="/static/icons/picture.png"')

    return string


class TestAuthenticate(LegacyAPITestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self, enable_signals):
        enable_signals()

        url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1})
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/mentor/session/1")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 GET without MentorshipSession
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.messages.storage.fallback.FallbackStorage.add", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__get__without_mentorship_session(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render(f"Session not found with id 1", token=model.token)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])
        self.assertEqual(FallbackStorage.add.call_args_list, [])

    """
    🔽🔽🔽 GET with MentorshipSession
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.messages.storage.fallback.FallbackStorage.add", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__get__with_mentorship_session(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(user=1, token=1, mentorship_session=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = (
            reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": model.mentorship_session.id})
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_form(self, model.mentorship_session, model.token, fix_logo=False)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_session),
                    "mentor_left_at": UTC_NOW,
                }
            ],
        )
        self.assertEqual(FallbackStorage.add.call_args_list, [])

    """
    🔽🔽🔽 GET with MentorshipSession, passing message
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.messages.storage.fallback.FallbackStorage.add", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__get__with_mentorship_session__passing_message(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(user=1, token=1, mentorship_session=1)

        message = self.bc.fake.slug()
        querystring = self.bc.format.to_querystring(
            {
                "token": model.token.key,
                "message": message,
            }
        )

        url = (
            reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": model.mentorship_session.id})
            + f"?{querystring}"
        )
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_form(self, model.mentorship_session, model.token, fix_logo=False)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                {
                    **self.bc.format.to_dict(model.mentorship_session),
                    "mentor_left_at": UTC_NOW,
                }
            ],
        )

        self.assertEqual(FallbackStorage.add.call_args_list, [call(20, message, "")])

    """
    🔽🔽🔽 GET with MentorshipSession
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.messages.storage.fallback.FallbackStorage.add", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__get__with_mentorship_session__without_mentee(self, enable_signals):
        enable_signals()

        statuses = [
            # 'PENDING',
            # 'STARTED',
            "COMPLETED",
            "FAILED",
            "IGNORED",
        ]
        for c in statuses:
            mentorship_sessions = [{"mentee_id": None}, {"status": c}]
            model = self.bc.database.create(
                user=1, token=1, mentorship_session=mentorship_sessions, mentorship_service=1
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": model.mentorship_session[0].id})
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_close_session(
                "Previous session expired without assigned mentee, it probably means the mentee "
                "never came. It was marked as failed. Try the mentor meeting URL again.",
                model.mentor_profile,
                model.user,
                model.token,
                model.mentorship_service,
                model.academy,
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
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session[0]),
                        "mentor_left_at": UTC_NOW,
                        "status": "FAILED",
                        "summary": (
                            "This session expired without assigned mentee, it probably "
                            "means the mentee never came. It will be marked as failed"
                        ),
                    },
                    {
                        **self.bc.format.to_dict(model.mentorship_session[1]),
                    },
                ],
            )
            self.assertEqual(FallbackStorage.add.call_args_list, [])

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 GET with MentorshipSession
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.messages.storage.fallback.FallbackStorage.add", MagicMock())
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test__get__with_mentorship_session__without_mentee__(self, enable_signals):
        enable_signals()

        statuses = [
            "PENDING",
            "STARTED",
        ]
        for c in statuses:
            mentorship_sessions = [{"mentee_id": None}, {"status": c}]
            model = self.bc.database.create(
                user=1, token=1, mentorship_session=mentorship_sessions, mentorship_service=1
            )

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = (
                reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": model.mentorship_session[0].id})
                + f"?{querystring}"
            )
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_close_session(
                "Previous session expired without assigned mentee, it probably means the mentee "
                "never came. It was marked as failed. Try the mentor meeting URL again.",
                model.mentor_profile,
                model.user,
                model.token,
                model.mentorship_service,
                model.academy,
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
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session[0]),
                        "mentor_left_at": UTC_NOW,
                        "status": "FAILED",
                        "summary": (
                            "This session expired without assigned mentee, it probably "
                            "means the mentee never came. It will be marked as failed"
                        ),
                    },
                    {
                        **self.bc.format.to_dict(model.mentorship_session[1]),
                    },
                ],
            )
            self.assertEqual(FallbackStorage.add.call_args_list, [])

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

            Token = self.bc.database.get_model("authenticate.Token")
            token = Token.objects.filter(user=model.user, token_type="temporal").last()

            calls = (
                []
                if c != "STARTED"
                else [
                    call(
                        "message",
                        model.mentor_profile.user.email,
                        {
                            "SUBJECT": "Mentorship session starting",
                            "MESSAGE": f"Mentee {model.user.first_name} {model.user.last_name} is joining your session, please come back to this email when the session is over to marke it as completed",
                            "BUTTON": f"Finish and review this session",
                            "LINK": f"/mentor/session/4?token={token.key}",
                        },
                        academy=model.academy,
                    )
                ]
            )
            self.bc.check.calls(actions.send_email_message.call_args_list, calls)

    """
    🔽🔽🔽 POST without MentorshipSession, passing nothing
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__without_mentorship_session__passing_nothing(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
        data = {}
        response = self.client.post(url, data, format="multipart")

        content = self.bc.format.from_bytes(response.content)

        expected = render_post_form(
            self, messages=[Message("alert-danger", f"Invalid or expired deliver token.")], token=model.token, data=data
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 POST without MentorshipSession, passing token
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__without_mentorship_session__passing_token(self, enable_signals):
        enable_signals()

        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
        data = {"token": model.token.key}
        response = self.client.post(url, data, format="multipart")

        content = self.bc.format.from_bytes(response.content)

        expected = render_post_form(
            self, messages=[Message("alert-danger", f"Invalid session id.")], token=model.token, data=data
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("mentorship.MentorshipSession"), [])

    """
    🔽🔽🔽 POST with MentorshipSession, passing token and session_id, without requires field
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__with_mentorship_session__passing_token__passing_session_id__without_requires_field(
        self, enable_signals
    ):
        enable_signals()

        model = self.bc.database.create(user=1, token=1, mentorship_session=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
        data = {"token": model.token.key, "session_id": 1}
        response = self.client.post(url, data, format="multipart")

        content = self.bc.format.from_bytes(response.content)
        expected = render_form(self, model.mentorship_session, model.token, data=data, post=True, fix_logo=False)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

    """
    🔽🔽🔽 POST with MentorshipSession, passing token and session_id, with requires field, good statuses
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__with_mentorship_session__passing_token__passing_session_id__with_requires_field__good_statuses(
        self, enable_signals
    ):
        enable_signals()

        statuses = ["COMPLETED", "FAILED", "IGNORED"]
        for s in statuses:
            model = self.bc.database.create(user=1, token=1, mentorship_session=1, mentorship_service=1)

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
            data = {
                "token": model.token.key,
                "session_id": model.mentorship_session.id,
                "summary": self.bc.fake.text(),
                "student_name": "Aaaaa",
                "status": s,
            }
            response = self.client.post(url, data, format="multipart")

            content = self.bc.format.from_bytes(response.content)
            url = f"/mentor/meet/{model.mentor_profile.slug}?token={model.token.key}"
            expected = render_close_session(
                f'The mentoring session was closed successfully, you can close this window or <a href="{url}">'
                "go back to your meeting room.</a>",
                model.mentor_profile,
                model.user,
                model.token,
                model.mentorship_service,
                model.academy,
                fix_logo=False,
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
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session),
                        "ended_at": UTC_NOW,
                        "status": data["status"],
                        "summary": data["summary"],
                    },
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")

    """
    🔽🔽🔽 POST with MentorshipSession, passing token and session_id, with requires field, bad statuses
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__post__with_mentorship_session__passing_token__passing_session_id__with_requires_field__bad_statuses(
        self, enable_signals
    ):
        enable_signals()

        statuses = ["PENDING", "STARTED"]
        for s in statuses:
            model = self.bc.database.create(user=1, token=1, mentorship_session=1)

            querystring = self.bc.format.to_querystring({"token": model.token.key})
            url = reverse_lazy("mentorship_shortner:session_id", kwargs={"session_id": 1}) + f"?{querystring}"
            data = {
                "token": model.token.key,
                "session_id": model.mentorship_session.id,
                "summary": self.bc.fake.text(),
                "student_name": "Aaaaa",
                "status": s,
            }
            response = self.client.post(url, data, format="multipart")

            content = self.bc.format.from_bytes(response.content)
            expected = render_form(self, model.mentorship_session, model.token, data=data, post=True, fix_logo=False)

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("mentorship.MentorshipSession"),
                [
                    {
                        **self.bc.format.to_dict(model.mentorship_session),
                        # 'status': data['status'],
                    },
                ],
            )

            # teardown
            self.bc.database.delete("mentorship.MentorshipSession")
