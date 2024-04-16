"""
Test /answer
"""
import json
import random
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from django.urls.base import reverse_lazy
from linked_services.django.actions import reset_app_cache
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    reset_app_cache()
    yield


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

    model = bc.database.create(profile_academy=1, app={'slug': 'rigobot', 'app_url': bc.fake.url()})
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', get=MagicMock(return_value=mock)):
        response = client.get(url)
        bc.check.calls(requests.get.call_args_list, [])

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
    model = bc.database.create(profile_academy=1, task=task, app={'slug': 'rigobot', 'app_url': bc.fake.url()})
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', get=MagicMock(return_value=mock)):
        response = client.get(url)
        bc.check.calls(requests.get.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"github-account-not-connected","status_code":400}'
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
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               })
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch('linked_services.django.actions.get_jwt', MagicMock(return_value=token)):
        with patch.multiple('requests', get=MagicMock(return_value=mock)):
            response = client.get(url)
            assert requests.get.call_args_list == [
                call(
                    model.app.app_url + '/v1/finetuning/me/coderevision',
                    params={
                        **query,
                        'repo': model.task.github_url,
                        'github_username': model.credentials_github.username,
                    },
                    stream=True,
                    headers={'Authorization': f'Link App=breathecode,Token={token}'},
                ),
            ]

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# When: no tasks
# Then: response 404
@pytest.mark.skip('Temporarily disabled')
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

    model = bc.database.create(profile_academy=1, app={'slug': 'rigobot', 'app_url': bc.fake.url()})
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(requests.post.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"not-enough-consumables","status_code":402}'
    assert response.status_code == 402
    assert bc.database.list_of('assignments.Task') == []


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

    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               permission=permission,
                               group=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               service=1,
                               service_set=service_set)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(requests.post.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"with-consumer-not-enough-consumables","status_code":402}'
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

    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               permission=permission,
                               group=1,
                               consumable=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               service=1,
                               service_set=service_set)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(requests.post.call_args_list, [])

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
    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               permission=permission,
                               group=1,
                               consumable=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               service=1,
                               service_set=service_set)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    with patch.multiple('requests', post=MagicMock(return_value=mock)):
        response = client.post(url)
        bc.check.calls(requests.post.call_args_list, [])

    assert response.getvalue().decode('utf-8') == '{"detail":"github-account-not-connected","status_code":400}'
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
    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               permission=permission,
                               group=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               consumable=1,
                               service=1,
                               service_set=service_set)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch('linked_services.django.actions.get_jwt', MagicMock(return_value=token)):
        with patch.multiple('requests', post=MagicMock(return_value=mock)):
            response = client.post(url, query, format='json')
            assert requests.post.call_args_list == [
                call(
                    model.app.app_url + '/v1/finetuning/coderevision/',
                    data=query,
                    json=None,
                    params={
                        **query,
                        'repo': model.task.github_url,
                        'github_username': model.credentials_github.username,
                    },
                    stream=True,
                    headers={'Authorization': f'Link App=breathecode,Token={token}'},
                ),
            ]

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# Given: A no SAAS student who has paid
# When: auth
# Then: response 200
@pytest.mark.parametrize('cohort_user', [
    {
        'finantial_status': 'FULLY_PAID',
        'educational_status': 'ACTIVE',
    },
    {
        'finantial_status': 'UP_TO_DATE',
        'educational_status': 'ACTIVE',
    },
])
@pytest.mark.parametrize('academy, cohort', [
    (
        {
            'available_as_saas': True
        },
        {
            'available_as_saas': False
        },
    ),
    (
        {
            'available_as_saas': False
        },
        {
            'available_as_saas': None
        },
    ),
])
def test__post__auth__no_saas__finantial_status_no_late(bc: Breathecode, client: APIClient, academy, cohort,
                                                        cohort_user):
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
    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               permission=permission,
                               group=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               consumable=1,
                               service=1,
                               service_set=service_set,
                               academy=academy,
                               cohort=cohort,
                               cohort_user=cohort_user)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch('linked_services.django.actions.get_jwt', MagicMock(return_value=token)):
        with patch.multiple('requests', post=MagicMock(return_value=mock)):
            response = client.post(url, query, format='json')
            assert requests.post.call_args_list == [
                call(
                    model.app.app_url + '/v1/finetuning/coderevision/',
                    data=query,
                    json=None,
                    params={
                        **query,
                        'repo': model.task.github_url,
                        'github_username': model.credentials_github.username,
                    },
                    stream=True,
                    headers={'Authorization': f'Link App=breathecode,Token={token}'},
                ),
            ]

    assert response.getvalue().decode('utf-8') == json.dumps(expected)
    assert response.status_code == code
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]


# Given: A no SAAS student who hasn't paid
# When: auth
# Then: response 402
@pytest.mark.parametrize('academy, cohort', [
    (
        {
            'available_as_saas': True
        },
        {
            'available_as_saas': False
        },
    ),
    (
        {
            'available_as_saas': False
        },
        {
            'available_as_saas': None
        },
    ),
])
def test__post__auth__no_saas__finantial_status_late(bc: Breathecode, client: APIClient, academy, cohort):
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
    permission = {'codename': 'add_code_review'}
    service_set = {'slug': 'code_revision'}
    cohort_user = {'finantial_status': 'LATE', 'educational_status': 'ACTIVE'}
    model = bc.database.create(profile_academy=1,
                               task=task,
                               credentials_github=credentials_github,
                               permission=permission,
                               group=1,
                               app={
                                   'slug': 'rigobot',
                                   'app_url': bc.fake.url()
                               },
                               consumable=1,
                               service=1,
                               service_set=service_set,
                               cohort_user=cohort_user,
                               cohort=cohort,
                               academy=academy)
    client.force_authenticate(model.user)

    url = reverse_lazy('assignments:me_task_id_coderevision', kwargs={'task_id': 1
                                                                      }) + '?' + bc.format.querystring(query)

    token = bc.random.string(lower=True, upper=True, symbol=True, number=True, size=20)
    with patch('linked_services.django.actions.get_jwt', MagicMock(return_value=token)):
        with patch.multiple('requests', post=MagicMock(return_value=mock)):
            response = client.post(url, query, format='json')
            assert requests.post.call_args_list == []

    x = response.json()
    expected = {'detail': 'cohort-user-status-later', 'status_code': 402}

    assert x == expected
    assert response.status_code == 402
    assert bc.database.list_of('assignments.Task') == [bc.format.to_dict(model.task)]
