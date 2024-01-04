"""
Test /answer
"""
import json
import random
from unittest.mock import MagicMock, call, patch
from rest_framework.test import APIClient

from django.urls.base import reverse_lazy
import pytest
from rest_framework import status
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

from breathecode.utils.service import Service


@pytest.fixture(autouse=True)
def setup(db):
    # setup logic
    yield
    # teardown logic


# When: no auth
# Then: response 401
def test_no_auth(bc: Breathecode, client: APIClient):
    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1})
    response = client.get(url)

    json = response.json()
    expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of('assignments.Task') == []


# When: no tasks
# Then: response 404
def test__get__no_tasks(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    model = bc.database.create(profile_academy=1)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        get=MagicMock(return_value=mock)):
        response = client.get(url)
        bc.check.calls(Service.get.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"task-not-found","status_code":404}'
    assert response.status_code == 404
    assert bc.database.list_of('assignments.Task') == []


# When: no github accounts
# Then: response 200
def test__get__no_github_accounts(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    task = {'github_url': bc.fake.url()}
    model = bc.database.create(profile_academy=1, task=task)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        get=MagicMock(return_value=mock)):
        response = client.get(url)
        bc.check.calls(Service.get.call_args_list, [])

    assert response.getvalue().decode(
        'utf-8') == '{"detail":"github-account-not-connected","status_code":400}'
    assert response.status_code == 400
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# When: auth
# Then: response 200
def test__get__auth(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    task = {'github_url': bc.fake.url()}
    credentials_github = {'username': bc.fake.slug()}
    model = bc.database.create(profile_academy=1, task=task, credentials_github=credentials_github)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        get=MagicMock(return_value=mock)):
        response = client.get(url)
        bc.check.calls(Service.get.call_args_list, [
            call('/v1/finetuning/me/coderevision',
                 params={
                     **query,
                     'repo': model.task.github_url,
                     'github_username': model.credentials_github.username,
                 },
                 stream=True),
        ])

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# When: no tasks
# Then: response 404
def test__post__no_consumables(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    model = bc.database.create(profile_academy=1)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(Service.post.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"not-enough-consumables","status_code":402}'
    assert response.status_code == 402
    assert bc.database.list_of('assignments.Task') == []


# When: no tasks
# Then: response 404
def test__post__no_tasks(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    permission = {'codename': 'get_code_review'}
    app_service = {'service': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               permission=permission,
                               group=1,
                               consumable=1,
                               service=1,
                               app_service=app_service)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(Service.post.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"task-not-found","status_code":404}'
    assert response.status_code == 404
    assert bc.database.list_of('assignments.Task') == []


# When: no github accounts
# Then: response 200
def test__post__no_github_accounts(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    task = {'github_url': bc.fake.url()}
    permission = {'codename': 'get_code_review'}
    app_service = {'service': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               permission=permission,
                               group=1,
                               consumable=1,
                               service=1,
                               app_service=app_service)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(Service.post.call_args_list, [])

    assert response.getvalue().decode(
        'utf-8') == '{"detail":"github-account-not-connected","status_code":400}'
    assert response.status_code == 400
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# When: auth
# Then: response 200
def test__post__auth(bc: Breathecode, client: APIClient):
    expected = {'data': {'getTask': {'id': random.randint(1, 100)}}}
    query = {
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
        bc.fake.slug(): bc.fake.slug(),
    }

    mock = MagicMock()
    mock.raw = iter([json.dumps(expected).encode()])
    mock.headers = {'Content-Type': 'application/json'}
    code = random.randint(200, 299)
    mock.status_code = code
    mock.reason = 'OK'

    task = {'github_url': bc.fake.url()}
    credentials_github = {'username': bc.fake.slug()}
    permission = {'codename': 'get_code_review'}
    app_service = {'service': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               permission=permission,
                               group=1,
                               consumable=1,
                               service=1,
                               app_service=app_service)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('breathecode.utils.service.Service',
                        __init__=MagicMock(return_value=None),
                        post=MagicMock(return_value=mock)):
        response = client.post(url, query, format='json')
        bc.check.calls(Service.post.call_args_list, [
            call('/v1/finetuning/coderevision/',
                 data=query,
                 params={
                     **query,
                     'repo': model.task.github_url,
                     'github_username': model.credentials_github.username,
                 },
                 stream=True),
        ])

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]
