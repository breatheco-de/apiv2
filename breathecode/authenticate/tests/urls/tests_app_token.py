"""
Test cases for /user
"""

from datetime import datetime, timedelta
from typing import Callable
from unittest.mock import MagicMock

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    from linked_services.django.actions import reset_app_cache

    reset_app_cache()
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())
    yield


def test_no_auth(bc: Breathecode, client: capy.Client):
    url = reverse_lazy("authenticate:app_token")
    response = client.post(url)

    json = response.json()
    expected = {
        "detail": "no-authorization-header",
        "status_code": status.HTTP_401_UNAUTHORIZED,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("authenticate.Token") == []


def test_external_app(bc: Breathecode, client: capy.Client, sign_jwt_link: Callable[..., None]):
    app = {"require_an_agreement": True, "slug": "rigobot"}
    model = bc.database.create(
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
    )

    sign_jwt_link(client, model.app)

    url = reverse_lazy("authenticate:app_token")
    response = client.post(url)

    json = response.json()
    expected = {"detail": "from-external-app", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.Token") == []


def test_no_data(bc: Breathecode, client: capy.Client, sign_jwt_link: Callable[..., None]):
    app = {"require_an_agreement": False, "slug": "rigobot"}
    model = bc.database.create(
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
    )

    sign_jwt_link(client, model.app)

    url = reverse_lazy("authenticate:app_token")
    response = client.post(url)

    json = response.json()
    expected = {"detail": "token-not-provided", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.Token") == []


@pytest.mark.parametrize("token_type", [None, "login", "temporal", "permanent"])
@pytest.mark.parametrize("delta", [-timedelta(hours=10), timedelta(0), timedelta(hours=10)])
def test_bad_token(
    bc: Breathecode,
    client: capy.Client,
    sign_jwt_link: Callable[..., None],
    token_type: str,
    delta: timedelta,
    utc_now: datetime,
    format: capy.Format,
):
    extra = {}
    app = {"require_an_agreement": False, "slug": "rigobot"}

    if token_type:
        extra["user"] = 1
        expires_at = None
        if delta:
            expires_at = utc_now + delta

        extra["token"] = {"token_type": token_type, "key": "1234", "expires_at": expires_at}

    model = bc.database.create(
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
        **extra,
    )

    sign_jwt_link(client, model.app)

    url = reverse_lazy("authenticate:app_token")
    data = {"token": "1234"}
    response = client.post(url, data)

    json = response.json()
    expected = {"detail": "invalid-token", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    if "token" in extra and (token_type == "permanent" or delta >= timedelta(0)):
        assert bc.database.list_of("authenticate.Token") == [format.to_obj_repr(model.token)]
    else:
        assert bc.database.list_of("authenticate.Token") == []


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(hours=10)])
def test_get_token(
    bc: Breathecode, client: capy.Client, sign_jwt_link: Callable[..., None], utc_now: datetime, delta: timedelta
):
    app = {"require_an_agreement": False, "slug": "rigobot"}
    expires_at = None
    if delta:
        expires_at = utc_now + delta
    model = bc.database.create(
        user=1,
        token={"token_type": "one_time", "key": "1234", "expires_at": expires_at},
        app=app,
        first_party_credentials={
            "app": {
                "rigobot": 1,
            },
        },
    )

    sign_jwt_link(client, model.app)

    url = reverse_lazy("authenticate:app_token")
    data = {"token": "1234"}
    response = client.post(url, data)

    json = response.json()
    expected = {
        "email": model.user.email,
        "expires_at": None,
        "token": "1234",
        "token_type": "one_time",
        "user_id": 1,
    }

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("authenticate.Token") == []
