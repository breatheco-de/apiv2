"""
Test /answer
"""

import json
import random
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import requests
from aiohttp import ClientSession
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
def patch_get(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(json.dumps(expected).encode())
        monkeypatch.setattr("aiohttp.ClientSession.get", MagicMock(return_value=ResponseMock(reader, code, headers)))

    yield handler


@pytest.fixture(autouse=True)
def patch_post(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(json.dumps(expected).encode())
        monkeypatch.setattr("aiohttp.ClientSession.post", MagicMock(return_value=ResponseMock(reader, code, headers)))

    yield handler


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1})
    response = client.get(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("assignments.Task") == []


# When: no tasks
# Then: response 404
def test__get__no_tasks(bc: Breathecode, client: APIClient, patch_get):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_get(expected, code, headers)

    model = bc.database.create(profile_academy=1, app={"slug": "rigobot", "app_url": bc.fake.url()})
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.get(url)
    assert ClientSession.get.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"task-not-found","status_code":404}'
    assert response.status_code == 404
    assert bc.database.list_of("assignments.Task") == []


# When: no github accounts
# Then: response 200
def test__get__no_github_accounts(bc: Breathecode, client: APIClient, patch_get):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_get(expected, code, headers)

    task = {"github_url": bc.fake.url()}
    model = bc.database.create(profile_academy=1, task=task, app={"slug": "rigobot", "app_url": bc.fake.url()})
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.get(url)
    assert ClientSession.get.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"github-account-not-connected","status_code":400}'
    assert response.status_code == 400
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# When: auth
# Then: response 200
def test__get__auth(bc: Breathecode, client: APIClient, patch_get):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_get(expected, code, headers)

    task = {"github_url": bc.fake.url()}
    credentials_github = {"username": bc.fake.slug()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        credentials_github=credentials_github,
        app={"slug": "rigobot", "app_url": bc.fake.url()},
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch("linked_services.django.actions.get_jwt", MagicMock(return_value=token)):
        response = client.get(url)
        assert ClientSession.get.call_args_list == [
            call(
                model.app.app_url + "/v1/finetuning/me/coderevision",
                params={
                    **query,
                    "repo": model.task.github_url,
                    "github_username": model.credentials_github.username,
                },
                headers={"Authorization": f"Link App=breathecode,Token={token}"},
            ),
        ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# When: no tasks
# Then: response 404
@pytest.mark.skip("Temporarily disabled")
def test__post__no_consumables(bc: Breathecode, client: APIClient, patch_post):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    model = bc.database.create(profile_academy=1, app={"slug": "rigobot", "app_url": bc.fake.url()})
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.post(url)
    assert ClientSession.post.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"not-enough-consumables","status_code":402}'
    assert response.status_code == 402
    assert bc.database.list_of("assignments.Task") == []


# When: no tasks
# Then: response 404
def test__post__no_consumables(bc: Breathecode, client: APIClient, patch_post):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    model = bc.database.create(
        profile_academy=1,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
        },
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.post(url)
    assert ClientSession.post.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"with-consumer-not-enough-consumables","status_code":402}'
    assert response.status_code == 402
    assert bc.database.list_of("assignments.Task") == []


# When: no tasks
# Then: response 404
def test__post__no_tasks(bc: Breathecode, client: APIClient, patch_post):
    expected = {"data": {"getTask": {"id": random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {"Content-Type": "application/json"}

    patch_post(expected, code, headers)

    model = bc.database.create(
        profile_academy=1,
        consumable=1,
        app={"slug": "rigobot", "app_url": bc.fake.url()},
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.post(url)
    assert ClientSession.post.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"task-not-found","status_code":404}'
    assert response.status_code == 404
    assert bc.database.list_of("assignments.Task") == []


# When: no github accounts
# Then: response 200
def test__post__no_github_accounts(bc: Breathecode, client: APIClient, patch_post):
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
        consumable=1,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
        },
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    response = client.post(url)
    assert ClientSession.post.call_args_list == []

    assert response.getvalue().decode("utf-8") == '{"detail":"github-account-not-connected","status_code":400}'
    assert response.status_code == 400
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# When: auth
# Then: response 200
def test__post__auth(bc: Breathecode, client: APIClient, patch_post):
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
    credentials_github = {"username": bc.fake.slug()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        credentials_github=credentials_github,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
        },
        consumable=1,
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch("linked_services.django.actions.get_jwt", MagicMock(return_value=token)):
        response = client.post(url, query, format="json")
        assert ClientSession.post.call_args_list == [
            call(
                model.app.app_url + "/v1/finetuning/coderevision/",
                data=query,
                json=None,
                params={
                    **query,
                    "repo": model.task.github_url,
                    "github_username": model.credentials_github.username,
                },
                headers={"Authorization": f"Link App=breathecode,Token={token}"},
            ),
        ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# Given: A no SAAS student who has paid
# When: auth
# Then: response 200
@pytest.mark.parametrize(
    "cohort_user",
    [
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "ACTIVE",
        },
        {
            "finantial_status": "FULLY_PAID",
            "educational_status": "GRADUATED",
        },
        {
            "finantial_status": "UP_TO_DATE",
            "educational_status": "GRADUATED",
        },
    ],
)
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
def test__post__auth__no_saas__finantial_status_no_late(
    bc: Breathecode, client: APIClient, academy, cohort, cohort_user, patch_post
):
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
    credentials_github = {"username": bc.fake.slug()}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        credentials_github=credentials_github,
        app={
            "slug": "rigobot",
            "app_url": bc.fake.url(),
        },
        consumable=1,
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
        academy=academy,
        cohort=cohort,
        cohort_user=cohort_user,
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch("linked_services.django.actions.get_jwt", MagicMock(return_value=token)):
        response = client.post(url, query, format="json")
        assert ClientSession.post.call_args_list == [
            call(
                model.app.app_url + "/v1/finetuning/coderevision/",
                data=query,
                json=None,
                params={
                    **query,
                    "repo": model.task.github_url,
                    "github_username": model.credentials_github.username,
                },
                headers={"Authorization": f"Link App=breathecode,Token={token}"},
            ),
        ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# Given: A no SAAS student who hasn't paid
# When: auth
# Then: response 402
@pytest.mark.parametrize(
    "academy, cohort",
    [
        (
            {"available_as_saas": True},
            {"available_as_saas": False},
        ),
        (
            {"available_as_saas": False},
            {"available_as_saas": None},
        ),
    ],
)
def test__post__auth__no_saas__finantial_status_late(bc: Breathecode, client: APIClient, academy, cohort, patch_post):
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
    credentials_github = {"username": bc.fake.slug()}
    cohort_user = {"finantial_status": "LATE", "educational_status": "ACTIVE"}
    model = bc.database.create(
        profile_academy=1,
        task=task,
        credentials_github=credentials_github,
        app={"slug": "rigobot", "app_url": bc.fake.url()},
        consumable=1,
        service={
            "type": "VOID",
            "slug": "add_code_review",
        },
        cohort_user=cohort_user,
        cohort=cohort,
        academy=academy,
    )
    client.force_authenticate(model.user)

    url = (
        reverse_lazy("assignments:me_task_id_coderevision", kwargs={"task_id": 1}) + "?" + bc.format.querystring(query)
    )

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch("linked_services.django.actions.get_jwt", MagicMock(return_value=token)):
        response = client.post(url, query, format="json")
        assert ClientSession.post.call_args_list == []

    x = response.json()
    expected = {"detail": "cohort-user-status-later", "status_code": 402}

    assert x == expected
    assert response.status_code == 402
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]
