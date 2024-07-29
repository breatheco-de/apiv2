"""
Test /answer
"""

import json
import random
from unittest.mock import AsyncMock, MagicMock, call, patch

import aiohttp
import pytest
from django.core.exceptions import SynchronousOnlyOperation
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


class StreamReaderMock:

    def __init__(self, data):
        self.data = data

    async def read(self):
        return self.data


class ResponseMock:

    def __init__(self, data, status=200, headers={}):
        self.content = data
        self.status = status
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


@pytest.fixture(autouse=True)
def patch_post(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(json.dumps(expected).encode())
        monkeypatch.setattr("aiohttp.ClientSession.post", MagicMock(return_value=ResponseMock(reader, code, headers)))

    yield handler


@pytest.fixture
def get_jwt(bc: Breathecode, monkeypatch):
    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    monkeypatch.setattr("linked_services.django.actions.get_jwt", MagicMock(return_value=token))
    yield token


@pytest.fixture(
    params=[
        (
            "linked_services.core.service.Service.__aenter__",
            Exception,
            "App rigobot not found",
            "app-not-found",
            404,
            True,
        ),
        (
            "linked_services.core.service.Service.__aenter__",
            SynchronousOnlyOperation,
            "Async is not supported by the worker",
            "no-async-support",
            500,
            True,
        ),
        ("aiohttp.ClientSession.post", Exception, "random exc", "unexpected-error", 500, False),
    ]
)
def post_exc(request, monkeypatch):
    path, exc, message, slug, code, is_async = request.param
    if is_async:

        def async_exc_mock(*args, **kwargs):
            raise exc(message)

        monkeypatch.setattr(path, async_exc_mock)

    else:

        class ContextMock:

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                raise exc(message)

            async def __aexit__(self, exc_type, exc, tb):
                pass

            def __enter__(self):
                raise exc(message)

            def __exit__(self, exc_type, exc, tb):
                pass

        async def async_exc_mock(message):
            raise exc(message)

        monkeypatch.setattr(path, ContextMock)

    yield {
        "slug": slug,
        "code": code,
    }


def post_serializer(user, credentials_github=None, profile=None):
    data = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "profile": None,
        "credentialsgithub": None,
    }

    if profile:
        data["profile"] = {
            "avatar_url": profile.avatar_url,
            "bio": profile.bio,
            "phone": profile.phone,
            "show_tutorial": profile.show_tutorial,
            "twitter_username": profile.twitter_username,
            "github_username": profile.github_username,
            "portfolio_url": profile.portfolio_url,
            "linkedin_url": profile.linkedin_url,
            "blog": profile.blog,
        }

    if credentials_github:
        data["credentialsgithub"] = {
            "github_id": credentials_github.github_id,
            "token": credentials_github.token,
            "email": credentials_github.email,
            "avatar_url": credentials_github.avatar_url,
            "name": credentials_github.name,
            "username": credentials_github.username,
            "blog": credentials_github.blog,
            "bio": credentials_github.bio,
            "company": credentials_github.company,
            "twitter_username": credentials_github.twitter_username,
        }

    return data


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})
    response = client.post(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("auth.User") == []


# When: external app
# Then: response 200
def test_external_app(bc: Breathecode, client: APIClient):
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
            "require_an_agreement": True,
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})
    response = client.post(url, query, format="json")

    expected = {"detail": "external-app", "silent": True, "silent_code": "external-app", "status_code": 400}
    json = response.json()

    assert json == expected
    assert response.status_code == 400
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]


# When: raise an exception
# Then: response 200
def test_raise_an_exception(bc: Breathecode, client: APIClient, post_exc):
    expected = {"detail": post_exc["slug"], "status_code": post_exc["code"]}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
            "require_an_agreement": False,
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})

    response = client.post(url, query, format="json")
    json = response.json()

    assert json == expected
    assert response.status_code == post_exc["code"]
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]


# When: auth
# Then: response 200
def test_auth(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
            "require_an_agreement": False,
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})

    response = client.post(url, query, format="json")

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/auth/app/user",
            json=None,
            data=post_serializer(model.user),
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]


# When: auth, with profile
# Then: response 200
def test_auth__with_profile(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        profile=1,
        task=task,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
            "require_an_agreement": False,
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})

    response = client.post(url, query, format="json")

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/auth/app/user",
            json=None,
            data=post_serializer(model.user, profile=model.profile),
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]


# When: auth, with credentials github
# Then: response 200
def test_auth__with_credentials_github(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        credentials_github=1,
        task=task,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
            "require_an_agreement": False,
        },
    )
    client.force_authenticate(model.user)

    url = reverse_lazy("authenticate:me_app_slug_sync", kwargs={"app_slug": "rigobot"})

    response = client.post(url, query, format="json")

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/auth/app/user",
            json=None,
            data=post_serializer(model.user, credentials_github=model.credentials_github),
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]
