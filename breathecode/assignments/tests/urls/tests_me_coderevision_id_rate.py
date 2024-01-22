"""
Test /answer
"""
import json
import random
from unittest.mock import MagicMock, call

import aiohttp
import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.authenticate.actions import reset_app_cache
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
        monkeypatch.setattr('aiohttp.ClientSession.post',
                            MagicMock(return_value=ResponseMock(reader, code, headers)))

    yield handler


@pytest.fixture
def get_jwt(bc: Breathecode, monkeypatch):
    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    monkeypatch.setattr('breathecode.authenticate.actions.get_jwt', MagicMock(return_value=token))
    yield token


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy('assignments:me_coderevision_id_rate', kwargs={'coderevision_id': 1})
    response = client.post(url)

    json = response.json()
    expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of('assignments.Task') == []


# When: auth
# Then: response 200
def test_auth(bc: Breathecode, client: APIClient, patch_post, get_jwt):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    code = random.randint(200, 299)
    headers = {'Content-Type': 'application/json'}

    patch_post(expected, code, headers)

    task = {'github_url': bc.fake.url()}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               })
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_coderevision_id_rate', kwargs={'coderevision_id': 1})

    response = client.post(url, query, format='json')

    assert aiohttp.ClientSession.post.call_args_list == [
        call(f'{model.app.app_url}/v1/finetuning/rate/coderevision/1',
             data=query,
             headers={'Authorization': f'Link App=4geeks,Token={get_jwt}'})
    ]

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]
