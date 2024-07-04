"""
Test cases for /academy/:id/member/:id
"""

import os
import random
import string
from random import randint
from unittest.mock import MagicMock, patch

from django.core.handlers.wsgi import WSGIRequest
from django.http import QueryDict
from django.template import loader
from django.test.client import FakePayload
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.authenticate.forms import PickPasswordForm

from ..mixins.new_auth_test_case import AuthTestCase


def set_password(self, raw_password):
    self.password = raw_password


class Message(str):
    tags: str

    def __init__(self, css_class, *_):
        self.tags = css_class
        return super().__init__()

    def __new__(cls, _, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)


def render(message, button=None, button_target="_blank", link=None):
    request = None
    return loader.render_to_string(
        "message.html",
        {"MESSAGE": message, "BUTTON": button, "BUTTON_TARGET": button_target, "LINK": link},
        request,
        using=None,
    )


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message):
    request = None
    context = {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None}

    return loader.render_to_string("message.html", context, request)


def render_pick_password(self, method, token, data, messages=[]):
    environ = {
        "HTTP_COOKIE": "",
        "PATH_INFO": f"/v1/auth/password/{token}",
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": method,
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
        "QUERY_STRING": "",
        "CONTENT_TYPE": "application/octet-stream",
    }
    request = WSGIRequest(environ)

    querystring = self.bc.format.to_querystring(data)
    data = QueryDict(querystring, mutable=True)
    data["token"] = token
    data["callback"] = ""

    form = PickPasswordForm(data)

    context = {"form": form}

    if messages:
        context["messages"] = messages

    return loader.render_to_string("form.html", context, request)


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 GET with bad token
    """

    def test__get__bad_token(self):
        url = reverse_lazy("authenticate:password_token", kwargs={"token": "token"})
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("The link has expired.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("auth.User"), [])

    """
    🔽🔽🔽 GET with token
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    def test__get__with_token(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            model = self.bc.database.create(**kwargs)

            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_password(self, "GET", token, data={})

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 GET with token and empty fields
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    def test__get__with_token__with_empty_fields(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            model = self.bc.database.create(**kwargs)

            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            response = self.client.get(url)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_password(self, "GET", token, data={"password1": "", "password2": ""})

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 POST with bad token
    """

    def test__post__bad_token(self):
        url = reverse_lazy("authenticate:password_token", kwargs={"token": "token"})
        response = self.client.post(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("The link has expired.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("auth.User"), [])

    """
    🔽🔽🔽 POST with token, password is empty
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    def test__post__with_token__password_is_empty(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            model = self.bc.database.create(**kwargs)

            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            data = {"password1": "", "password2": ""}
            response = self.client.post(url, data)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_password(
                self, "POST", token, data=data, messages=[Message("alert-danger", "Password can't be empty")]
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 POST with token, password don't match
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    def test__post__with_token__password_does_not_match(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            model = self.bc.database.create(**kwargs)

            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            data = {"password1": self.bc.fake.password(), "password2": self.bc.fake.password()}
            response = self.client.post(url, data)

            content = self.bc.format.from_bytes(response.content)
            expected = render_pick_password(
                self, "POST", token, data=data, messages=[Message("alert-danger", "Passwords don't match")]
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            self.assertEqual(content, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 POST with token, invalid password
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    def test__post__with_token__invalid_password(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            passwords = [
                "".join(random.choices(string.ascii_lowercase, k=random.randint(1, 7))),
                "".join(random.choices(string.ascii_uppercase, k=random.randint(1, 7))),
                "".join(random.choices(string.punctuation, k=random.randint(1, 7))),
            ]
            for password in passwords:
                model = self.bc.database.create(**kwargs)

                url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
                data = {"password1": password, "password2": password}
                response = self.client.post(url, data)

                content = self.bc.format.from_bytes(response.content)
                expected = render_pick_password(
                    self,
                    "POST",
                    token,
                    data=data,
                    messages=[
                        Message(
                            "alert-danger", "Password must contain 8 characters with lowercase, uppercase and symbols"
                        )
                    ],
                )

                # dump error in external files
                if content != expected:
                    with open("content.html", "w") as f:
                        f.write(content)

                    with open("expected.html", "w") as f:
                        f.write(expected)

                self.assertEqual(content, expected)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

                # teardown
                self.bc.database.delete("auth.User")
                self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 POST with token, right password
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.auth.models.User.set_password", set_password)
    def test__post__with_token__right_password(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            password_characters = (
                random.choices(string.ascii_lowercase, k=3)
                + random.choices(string.ascii_uppercase, k=3)
                + random.choices(string.punctuation, k=2)
            )

            random.shuffle(password_characters)

            password = "".join(password_characters)

            model = self.bc.database.create(**kwargs)

            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            data = {"password1": password, "password2": password}
            response = self.client.post(url, data)

            content = self.bc.format.from_bytes(response.content)
            expected = render(
                "You password has been successfully set.",
                button="Continue to sign in",
                button_target="_self",
                link=os.getenv("APP_URL", "https://4geeks.com") + "/login",
            )

            # dump error in external files
            if content != expected:
                with open("content.html", "w") as f:
                    f.write(content)

                with open("expected.html", "w") as f:
                    f.write(expected)

            assert content == expected
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("auth.User"),
                [
                    {
                        **self.bc.format.to_dict(model.user),
                        "password": password,
                    },
                ],
            )

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")

    """
    🔽🔽🔽 POST with token, right password, passing callback
    """

    @patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken"))
    @patch("django.contrib.auth.models.User.set_password", set_password)
    def test__post__with_token__right_password__passing_callback(self):
        email = self.bc.fake.email()
        user = {"password": "", "email": email}
        token = {"key": "xyz"}
        user_invite = {"token": "abc", "email": email}

        cases = [({"user": user, "token": token}, "xyz"), ({"user": user, "user_invite": user_invite}, "abc")]
        for kwargs, token in cases:
            password_characters = (
                random.choices(string.ascii_lowercase, k=3)
                + random.choices(string.ascii_uppercase, k=3)
                + random.choices(string.punctuation, k=2)
            )

            random.shuffle(password_characters)

            password = "".join(password_characters)
            model = self.bc.database.create(**kwargs)

            redirect_url = self.bc.fake.url()
            url = reverse_lazy("authenticate:password_token", kwargs={"token": token})
            data = {"password1": password, "password2": password, "callback": redirect_url}
            response = self.client.post(url, data)

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
            self.assertEqual(response.url, redirect_url)
            self.assertEqual(
                self.bc.database.list_of("auth.User"),
                [
                    {
                        **self.bc.format.to_dict(model.user),
                        "password": password,
                    },
                ],
            )

            # teardown
            self.bc.database.delete("auth.User")
            self.bc.database.delete("authenticate.UserInvite")
