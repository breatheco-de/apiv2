import json
from unittest.mock import MagicMock, call, patch
from rest_framework.test import APIRequestFactory
import breathecode.utils.views as views
from rest_framework import status
from django.contrib.sessions.backends.db import SessionStore
from django.contrib import messages
from django.http import JsonResponse

from ..mixins import UtilsTestCase

PERMISSION = "can_kill_kenny"


def build_view(*args, **kwargs):

    @views.private_view(*args, **kwargs)
    def endpoint(request, token, id):
        return JsonResponse({"method": request.method, "id": id, "user": request.user.id, "token": token.key})

    return endpoint


class FunctionBasedViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 No token provided
    """

    # When: no token and not auth url
    # Then: it must redirect to the default auth url
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_nobody_was_provide(self):
        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny")

        session = SessionStore("blablabla")
        request.session = session

        view = build_view("can_kill_kenny")

        response = view(request, id=1)

        url_hash = self.bc.format.to_base64("/they-killed-kenny")
        content = self.bc.format.from_bytes(response.content, "utf-8")

        self.assertEqual(content, "")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={url_hash}")
        self.bc.check.calls(
            messages.add_message.call_args_list,
            [
                call(request, messages.ERROR, "Please login before you can access this view"),
            ],
        )

    # When: no token and auth url as arg
    # Then: it must redirect to the provided auth url
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_auth_url_as_arg(self):
        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny")

        session = SessionStore("blablabla")
        request.session = session

        url = self.bc.fake.url()
        view = build_view("can_kill_kenny", url)

        response = view(request, id=1)

        url_hash = self.bc.format.to_base64("/they-killed-kenny")
        content = self.bc.format.from_bytes(response.content, "utf-8")

        self.assertEqual(content, "")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, f"{url}?attempt=1&url={url_hash}")
        self.bc.check.calls(
            messages.add_message.call_args_list,
            [
                call(request, messages.ERROR, "Please login before you can access this view"),
            ],
        )

    # When: no token and auth url as kwarg
    # Then: it must redirect to the provided auth url
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_auth_url_as_kwarg(self):
        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny")

        session = SessionStore("blablabla")
        request.session = session

        url = self.bc.fake.url()
        view = build_view("can_kill_kenny", auth_url=url)

        response = view(request, id=1)

        url_hash = self.bc.format.to_base64("/they-killed-kenny")
        content = self.bc.format.from_bytes(response.content, "utf-8")

        self.assertEqual(content, "")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, f"{url}?attempt=1&url={url_hash}")
        self.bc.check.calls(
            messages.add_message.call_args_list,
            [
                call(request, messages.ERROR, "Please login before you can access this view"),
            ],
        )

    """
    🔽🔽🔽 Token provided
    """

    # Given: 1 Token
    # When: with token and not auth url
    # Then: return 200
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_token(self):
        model = self.bc.database.create(token=1)
        factory = APIRequestFactory()
        request = factory.get(f"/they-killed-kenny?token={model.token}")

        session = SessionStore("blablabla")
        request.session = session

        view = build_view()

        response = view(request, id=1)
        content = json.loads(self.bc.format.from_bytes(response.content, "utf-8"))

        self.assertEqual(content, {"method": "GET", "id": 1, "user": 1, "token": model.token.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bc.check.calls(messages.add_message.call_args_list, [])

    # Given: 1 Token
    # When: with token, no auth url and no permission
    # Then: it must redirect to the default auth url
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_token__passing_permission(self):
        model = self.bc.database.create(token=1)
        factory = APIRequestFactory()
        request = factory.get(f"/they-killed-kenny?token={model.token}")

        session = SessionStore("blablabla")
        request.session = session

        view = build_view("can_kill_kenny")

        response = view(request, id=1)

        url_hash = self.bc.format.to_base64(f"/they-killed-kenny?token={model.token}")
        content = self.bc.format.from_bytes(response.content, "utf-8")

        self.assertEqual(content, "")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={url_hash}")
        self.bc.check.calls(
            messages.add_message.call_args_list,
            [
                call(request, messages.ERROR, "You don't have permission can_kill_kenny to access this view"),
            ],
        )

    # Given: 1 Token
    # When: with token, auth url and no permission
    # Then: it must redirect to the default auth url
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_token__passing_permission__auth_url(self):
        model = self.bc.database.create(token=1)
        factory = APIRequestFactory()
        request = factory.get(f"/they-killed-kenny?token={model.token}")

        session = SessionStore("blablabla")
        request.session = session

        url = self.bc.fake.url()
        view = build_view("can_kill_kenny", url)

        response = view(request, id=1)

        url_hash = self.bc.format.to_base64(f"/they-killed-kenny?token={model.token}")
        content = self.bc.format.from_bytes(response.content, "utf-8")

        self.assertEqual(content, "")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, f"{url}?attempt=1&url={url_hash}")
        self.bc.check.calls(
            messages.add_message.call_args_list,
            [
                call(request, messages.ERROR, "You don't have permission can_kill_kenny to access this view"),
            ],
        )

    # Given: 1 Token
    # When: with token and not auth url
    # Then: return 200
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_token__with_permission(self):
        permission = {"codename": "can_kill_kenny"}
        model = self.bc.database.create(token=1, permission=permission, user=1)
        factory = APIRequestFactory()
        request = factory.get(f"/they-killed-kenny?token={model.token}")

        session = SessionStore("blablabla")
        request.session = session

        view = build_view("can_kill_kenny")

        response = view(request, id=1)
        content = json.loads(self.bc.format.from_bytes(response.content, "utf-8"))

        self.assertEqual(content, {"method": "GET", "id": 1, "user": 1, "token": model.token.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bc.check.calls(messages.add_message.call_args_list, [])

    # Given: 1 Token
    # When: with token and auth url
    # Then: return 200
    @patch("django.contrib.messages.add_message", MagicMock())
    def test_with_token__with_permission__auth_url(self):
        permission = {"codename": "can_kill_kenny"}
        model = self.bc.database.create(token=1, permission=permission, user=1)
        factory = APIRequestFactory()
        request = factory.get(f"/they-killed-kenny?token={model.token}")

        session = SessionStore("blablabla")
        request.session = session

        url = self.bc.fake.url()
        view = build_view("can_kill_kenny", url)

        response = view(request, id=1)
        content = json.loads(self.bc.format.from_bytes(response.content, "utf-8"))

        self.assertEqual(content, {"method": "GET", "id": 1, "user": 1, "token": model.token.key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bc.check.calls(messages.add_message.call_args_list, [])
