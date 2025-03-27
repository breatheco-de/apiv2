"""
Test /v1/auth/subscribe
"""

from typing import Any
from urllib.parse import urlencode

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

now = timezone.now()


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_SECRET", "123456")
    monkeypatch.setenv("GOOGLE_REDIRECT_URL", "https://breathecode.herokuapp.com/v1/auth/google/callback")
    monkeypatch.setenv("SET_GOOGLE_CREDENTIALS", "true")

    yield


def test_no_url(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:google_token", kwargs={"token": "78c9c2defd3be7f3f5b3ddd542ade55a2d35281b"})
    response = client.get(url, format="json")

    json = response.json()
    expected = {"detail": "no-callback-url", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "token",
    [
        0,
        {"token_type": "permanent"},
        {"token_type": "login"},
    ],
)
def test_invalid_token(database: capy.Database, client: capy.Client, token: Any):
    key = "78c9c2defd3be7f3f5b3ddd542ade55a2d35281b"
    model = database.create(token=token)
    if "token" in model:
        key = model.token.key

    url = reverse_lazy("authenticate:google_token", kwargs={"token": key}) + "?url=https://4geeks.com"
    response = client.get(url, format="json")

    json = response.json()
    expected = {"detail": "invalid-token", "status_code": 403}

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "token",
    [
        {"token_type": "temporal"},
    ],
)
def test_redirect(database: capy.Database, client: capy.Client, token: Any):
    model = database.create(token=token)
    callback_url = "https://4geeks.com/"

    url = reverse_lazy("authenticate:google_token", kwargs={"token": model.token.key}) + f"?url={callback_url}"
    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_302_FOUND
    params = {
        "response_type": "code",
        "client_id": "123456.apps.googleusercontent.com",
        "redirect_uri": "https://breathecode.herokuapp.com/v1/auth/google/callback",
        "access_type": "offline",
        "scope": " ".join(
            [
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/meetings.space.created",
                "https://www.googleapis.com/auth/drive.meet.readonly",
            ]
        ),
        "state": f"token={model.token.key}&url={callback_url}&academysettings=none",
    }

    assert response.url == f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


@pytest.mark.parametrize(
    "token",
    [
        {"token_type": "temporal"},
    ],
)
@pytest.mark.parametrize(
    "academy_settings",
    [
        "overwrite",
        "set",
    ],
)
def test_redirect_with_academy_settings(
    database: capy.Database, client: capy.Client, token: Any, academy_settings: str
):
    model = database.create(token=token)
    callback_url = "https://4geeks.com/"

    url = (
        reverse_lazy("authenticate:google_token", kwargs={"token": model.token.key})
        + f"?url={callback_url}&academysettings={academy_settings}"
    )
    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_302_FOUND
    params = {
        "response_type": "code",
        "client_id": "123456.apps.googleusercontent.com",
        "redirect_uri": "https://breathecode.herokuapp.com/v1/auth/google/callback",
        "access_type": "offline",
        "scope": " ".join(
            [
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/meetings.space.created",
                "https://www.googleapis.com/auth/drive.meet.readonly",
                "https://www.googleapis.com/auth/pubsub",
            ]
        ),
        "state": f"token={model.token.key}&url={callback_url}&academysettings={academy_settings}",
    }

    assert response.url == f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
