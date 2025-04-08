"""
Test /code-compiler
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
    url = reverse_lazy("registry:code_compiler")
    response = client.post(url)

    json = response.json()
    expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# When: auth and no additional context
# Then: response 200
def test_code_compiler(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    url = reverse_lazy("registry:code_compiler")
    model = bc.database.create(
        user=1,
        app={"slug": "rigobot"},
    )
    client.force_authenticate(model.user)

    expected = {
        "id": 62,
        "status": "PENDING",
        "status_text": None,
        "answer": "---terminal output---\nHello, world!\n",
        "inputs": {"code": "print('Hello, world!')", "language_and_version": "python"},
        "started_at": "2024-09-06T20:07:31.668065Z",
    }

    headers = {"Content-Type": "application/json"}

    data = {
        "execute_async": False,
        "include_organization_brief": False,
        "include_purpose_objective": True,
        "inputs": {"code": "print('Hello, world!')", "language_and_version": "python"},
    }

    patch_post(expected, 200, headers)
    response = client.post(url, data, format="json")

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/prompting/completion/code-compiler/",
            json=data,
            data=None,
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == status.HTTP_200_OK


# When: auth and with additional context
# Then: response 200
def test_code_compiler_with_context(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    url = reverse_lazy("registry:code_compiler")
    model = bc.database.create(
        user=1,
        app={"slug": "rigobot"},
    )
    client.force_authenticate(model.user)

    expected = {
        "id": 62,
        "status": "PENDING",
        "status_text": None,
        "answer": "---terminal output---\nHello, world!\n",
        "inputs": {
            "main_file": "File path: /main.py\nFile content:\nprint('Hello World!')",
            "language_and_version": "python",
            "secondary_files": "fileContext",
        },
        "started_at": "2024-09-06T20:07:31.668065Z",
    }

    headers = {"Content-Type": "application/json"}

    data = {
        "execute_async": False,
        "include_organization_brief": False,
        "include_purpose_objective": True,
        "inputs": {
            "main_file": "File path: /main.py\nFile content:\nprint('Hello World!')",
            "language_and_version": "python",
            "secondary_files": "fileContext",
        },
    }

    patch_post(expected, 200, headers)
    response = client.post(url, data, format="json")

    assert aiohttp.ClientSession.post.call_args_list == [
        call(
            f"{model.app.app_url}/v1/prompting/completion/code-compiler-with-context/",
            json=data,
            data=None,
            headers={"Authorization": f"Link App=breathecode,Token={get_jwt}"},
        )
    ]

    assert response.getvalue().decode("utf-8") == json.dumps(expected)
    assert response.status_code == status.HTTP_200_OK
