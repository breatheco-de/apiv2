"""
Test /v1/auth/subscribe
"""

import base64
import os
import random
from datetime import datetime
from unittest.mock import MagicMock, call
from urllib.parse import urlencode

import pytest
from capyc import pytest as capy
from django import shortcuts
from django.http import JsonResponse
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

now = timezone.now()


@pytest.fixture(autouse=True)
def redirect_url(monkeypatch: pytest.MonkeyPatch):
    def redirect_url(*args, **kwargs):

        if args:
            args = args[1:]

        if args:
            try:
                kwargs["_template"] = args[0]
            except:
                ...

            try:
                kwargs["context"] = args[1]
            except:
                ...

            try:
                if args[2]:
                    kwargs["content_type"] = args[2]
            except:
                ...

            try:
                if args[3]:
                    kwargs["status"] = args[3]
            except:
                ...

            try:
                if args[4]:
                    kwargs["using"] = args[4]
            except:
                ...

        if "context" in kwargs:
            kwargs.update(kwargs["context"])
            del kwargs["context"]

        if "academy" in kwargs:
            kwargs["academy"] = kwargs["academy"].id

        return JsonResponse(kwargs, status=kwargs["status"])

    monkeypatch.setattr(
        shortcuts,
        "render",
        MagicMock(side_effect=redirect_url),
    )
    yield


b = os.urandom(16)


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):

    monkeypatch.setattr("os.urandom", lambda _: b)
    monkeypatch.setattr("breathecode.authenticate.tasks.create_user_from_invite.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.verify_user_invite_email.delay", MagicMock())
    monkeypatch.setattr("rest_framework.authtoken.models.Token.generate_key", MagicMock(return_value="1234567890"))

    yield


@pytest.fixture
def validation_res(patch_request):
    validation_res = {
        "quality_score": (random.random() * 0.4) + 0.6,
        "email_quality": (random.random() * 0.4) + 0.6,
        "is_valid_format": {
            "value": True,
        },
        "is_mx_found": {
            "value": True,
        },
        "is_smtp_valid": {
            "value": True,
        },
        "is_catchall_email": {
            "value": True,
        },
        "is_role_email": {
            "value": True,
        },
        "is_disposable_email": {
            "value": False,
        },
        "is_free_email": {
            "value": True,
        },
    }
    patch_request(
        [
            (
                call(
                    "get",
                    "https://emailvalidation.abstractapi.com/v1/?api_key=None&email=pokemon@potato.io",
                    params=None,
                    timeout=10,
                ),
                validation_res,
            ),
        ]
    )
    return validation_res


def test_no_auth(database: capy.Database, client: APIClient):
    url = reverse_lazy("authenticate:academy_google")
    response = client.get(url)

    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == f'/v1/auth/view/login?attempt=1&url={base64.b64encode(url.encode("utf-8")).decode("utf-8")}'
    assert database.list_of("authenticate.Token") == []


def test_no_callback_url(database: capy.Database, client: APIClient, format: capy.Format):
    model = database.create(token=1, user=1)
    url = reverse_lazy("authenticate:academy_google") + f"?token={model.token.key}"
    response = client.get(url, headers={"Academy": 1})

    json = response.json()
    assert json == {
        "status": 400,
        "_template": "message.html",
        "MESSAGE": "no callback URL specified",
        "BUTTON": "Back to 4Geeks",
        "BUTTON_TARGET": "_blank",
        "LINK": os.getenv("APP_URL"),
    }

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert database.list_of("authenticate.Token") == [
        format.to_obj_repr(model.token),
    ]


def test_redirect_to_google(database: capy.Database, client: APIClient, format: capy.Format, utc_now: datetime):
    model = database.create(token=1, user=1)
    print(utc_now)
    url = reverse_lazy("authenticate:academy_google") + f"?token={model.token.key}&url=https://potato.io"
    response = client.get(url, headers={"Academy": 1})

    assert response.status_code == status.HTTP_302_FOUND

    query_params = {
        "url": "https://potato.io",
    }
    query_string = urlencode(query_params)

    assert response.url == f"/v1/auth/google/1234567890?{query_string}"
    assert database.list_of("authenticate.Token") == [
        format.to_obj_repr(model.token),
        {
            "id": 2,
            "key": "1234567890",
            "user_id": model.user.id,
            "expires_at": None,
            "created": model.token.created,
            "token_type": "one_time",
        },
    ]


@pytest.mark.parametrize("academy_settings", ["overwrite", "set"])
def test_no_capability_with_academy_settings(
    database: capy.Database, client: APIClient, format: capy.Format, utc_now: datetime, academy_settings: str
):
    model = database.create(token=1, user=1)
    print(utc_now)
    url = (
        reverse_lazy("authenticate:academy_google")
        + f"?token={model.token.key}&url=https://potato.io&academysettings={academy_settings}"
    )
    response = client.get(url, headers={"Academy": 1})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    json = response.json()
    assert json == {
        "status": 403,
        "_template": "message.html",
        "LINK": None,
        "MESSAGE": "You don't have permission to access this view",
        "BUTTON": None,
        "BUTTON_TARGET": "_blank",
    }

    assert database.list_of("authenticate.Token") == [
        format.to_obj_repr(model.token),
    ]


@pytest.mark.parametrize("academy_settings", ["overwrite", "set"])
def test_redirect_to_google_with_academy_settings(
    database: capy.Database, client: APIClient, format: capy.Format, utc_now: datetime, academy_settings: str
):
    model = database.create(
        token=1,
        user=1,
        academy=1,
        profile_academy=1,
        role=1,
        capability={"slug": "crud_academy_auth_settings"},
        city=1,
        country=1,
    )
    print(utc_now)
    url = (
        reverse_lazy("authenticate:academy_google")
        + f"?token={model.token.key}&url=https://potato.io&academysettings={academy_settings}"
    )
    response = client.get(url, headers={"Academy": 1})

    assert response.status_code == status.HTTP_302_FOUND

    query_params = {
        "academysettings": academy_settings,
        "url": "https://potato.io",
    }
    query_string = urlencode(query_params)

    assert response.url == f"/v1/auth/google/1234567890?{query_string}"
    assert database.list_of("authenticate.Token") == [
        format.to_obj_repr(model.token),
        {
            "id": 2,
            "key": "1234567890",
            "user_id": model.user.id,
            "expires_at": None,
            "created": model.token.created,
            "token_type": "one_time",
        },
    ]
