"""
Test /answer
"""

import json
import random
from unittest.mock import MagicMock, call, patch

import aiohttp
import pytest
import requests
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from linked_services.django.service import Service
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


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy("assignments:completion_job", kwargs={"task_id": 1})
    response = client.post(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of("assignments.Task") == []


# When: no task
# Then: response 404
def test_task_not_found(bc: Breathecode, client: APIClient):
    url = reverse_lazy("assignments:completion_job", kwargs={"task_id": 1})
    model = bc.database.create(profile_academy=1)
    client.force_authenticate(model.user)
    response = client.post(url)

    json = response.json()
    expected = {"detail": "task-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("assignments.Task") == []


# When: no asset
# Then: response 404
def test_asset_not_found(bc: Breathecode, client: APIClient):
    url = reverse_lazy("assignments:completion_job", kwargs={"task_id": 1})
    model = bc.database.create(profile_academy=1, task=1)
    client.force_authenticate(model.user)
    response = client.post(url)

    json = response.json()
    expected = {"detail": "asset-not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]


# When: auth and asset
# Then: response 200
def test_with_asset_and_task(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    url = reverse_lazy("assignments:completion_job", kwargs={"task_id": 1})
    model = bc.database.create(
        profile_academy=1,
        cohort=1,
        syllabus_version=1,
        syllabus={"name": "syllabus"},
        task={"associated_slug": "slayer"},
        asset={"slug": "slayer", "asset_type": "LESSON"},
        app={"slug": "rigobot"},
    )
    client.force_authenticate(model.user)

    expected = {
        "id": 62,
        "status": "PENDING",
        "status_text": None,
        "template": {"id": 5, "name": "Create post from document"},
        "inputs": {
            "asset_type": "LESSON",
            "title": "Learnpack",
            "syllabus_name": "Full-Stack Software Developer",
            "asset_markdown_body": "",
        },
        "started_at": "2024-09-06T20:07:31.668065Z",
    }

    headers = {"Content-Type": "application/json"}

    patch_post(expected, 201, headers)
    response = client.post(url, format="json")

    body = {
        "inputs": {
            "asset_type": model.task.task_type,
            "title": model.task.title,
            "syllabus_name": "syllabus",
            "asset_mardown_body": None,
        },
        "include_organization_brief": False,
        "include_purpose_objective": True,
        "execute_async": False,
        "just_format": True,
    }

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/prompting/completion/linked/5/",
            json=body,
            data=None,
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("assignments.Task") == [bc.format.to_dict(model.task)]
