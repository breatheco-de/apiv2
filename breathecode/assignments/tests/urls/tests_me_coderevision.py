"""
Test /answer
"""
import json
import random
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from aiohttp import ClientSession
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
def patch_get(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(json.dumps(expected).encode())
        monkeypatch.setattr('aiohttp.ClientSession.get', MagicMock(return_value=ResponseMock(reader, code, headers)))

    yield handler


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy('assignments:me_coderevision')
    response = client.get(url)

    json = response.json()
    expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of('assignments.Task') == []


# When: no github account
# Then: response 200
def test__no_github_account(bc: Breathecode, client: APIClient, patch_get):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {'Content-Type': 'application/json'}

    patch_get(expected, code, headers)

    task = {'github_url': bc.fake.url()}
    model = bc.database.create(profile_academy=1, task=task)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_coderevision') + '?' + bc.format.querystring(query)

    response = client.get(url)
    assert ClientSession.get.call_args_list == []

    assert response.getvalue().decode('utf-8') == '{"detail":"github-account-not-connected","status_code":400}'
    assert response.status_code == 400
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# When: auth in get
# Then: response 200
def test__get__auth(bc: Breathecode, client: APIClient, patch_get):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {'Content-Type': 'application/json'}

    patch_get(expected, code, headers)

    task = {'github_url': bc.fake.url()}
    credentials_github = {'username': bc.fake.slug()}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               app={'slug': 'rigobot'})
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_coderevision') + '?' + bc.format.querystring(query)

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch('linked_services.django.actions.get_jwt', MagicMock(return_value=token)):
        response = client.get(url)
        assert ClientSession.get.call_args_list == [
            call(model.app.app_url + '/v1/finetuning/me/coderevision',
                 params={
                     **query,
                     'github_username': model.credentials_github.username,
                 },
                 headers={'Authorization': f'Link App=breathecode,Token={token}'}),
        ]

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]
