"""
Test /answer
"""

import json
import random
from unittest.mock import MagicMock, call

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


@pytest.fixture
def patch_get(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(json.dumps(expected).encode())
        monkeypatch.setattr("aiohttp.ClientSession.get", MagicMock(return_value=ResponseMock(reader, code, headers)))

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
        ("aiohttp.ClientSession.get", Exception, "random exc", "unexpected-error", 500, False),
    ]
)
def get_exc(request, monkeypatch):
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


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("assignments:academy_task_id_commitfile", kwargs={"task_id": 1})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("assignments.Task") == []


# When: no capability
# Then: response 403
def test_no_capability(bc: Breathecode, client: APIClient):
    model = bc.database.create(user=1)

    client.force_authenticate(model.user)

    url = reverse_lazy("assignments:academy_task_id_commitfile", kwargs={"task_id": 1})
    response = client.get(url, headers={"academy": 1, "accept": "application/json"})

    json = response.json()
    expected = {
        "detail": "You (user: 1) don't have this capability: read_assignment for academy 1",
        "status_code": 403,
    }

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert bc.database.list_of("assignments.Task") == []


# When: raise an exception
# Then: response 200
def test_raise_an_exception(bc: Breathecode, client: APIClient, get_exc):
    expected = {"detail": get_exc["slug"], "status_code": get_exc["code"]}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        role=1,
        capability="read_assignment",
        app={"slug": "rigobot", "app_url": bc.fake.url()},
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:academy_task_id_commitfile", kwargs={"task_id": 1})
        + "?"
        + bc.format.querystring(query)
    )

    response = client.get(url, query, format="json", headers={"Academy": 1, "accept": "application/json"})
    json = response.json()

    assert json == expected
    assert response.status_code == get_exc["code"]
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# When: auth
# Then: response 200
def test_not_found(bc: Breathecode, client: APIClient, patch_get, get_jwt):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    headers = {"Content-Type": "application/json"}
    code = random.randint(200, 299)

    model = bc.database.create(
        profile_academy=1, role=1, capability="read_assignment", app={"slug": "rigobot", "app_url": bc.fake.url()}
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:academy_task_id_commitfile", kwargs={"task_id": 1})
        + "?"
        + bc.format.querystring(query)
    )

    patch_get(expected, code, headers)

    response = client.get(url, headers={"academy": 1, "accept": "application/json"})
    json = response.json()
    assert aiohttp.ClientSession.get.call_args_list == []

    assert json == {"detail": "task-not-found", "status_code": 404}
    assert response.status_code == 404
    assert bc.database.list_of("assignments.Task") == []


# When: auth
# Then: response 200
def test_auth(bc: Breathecode, client: APIClient, patch_get, get_jwt):
    # bc.request.set_headers(academy=1)

    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    headers = {"Content-Type": "application/json"}
    code = random.randint(200, 299)

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        role=1,
        capability="read_assignment",
        app={"slug": "rigobot", "app_url": bc.fake.url()},
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:academy_task_id_commitfile", kwargs={"task_id": 1})
        + "?"
        + bc.format.querystring(query)
    )

    patch_get(expected, code, headers)

    response = client.get(url, headers={"academy": 1, "accept": "application/json"})
    json = response.json()
    assert aiohttp.ClientSession.get.call_args_list == [
        call(
            f"{model.app.app_url}/v1/finetuning/commitfile",
            params={
                **query,
                "repo": model.task.github_url,
            },
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert json == expected
    assert response.status_code == code
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]
