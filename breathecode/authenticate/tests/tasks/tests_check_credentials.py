import logging
import random
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from breathecode.authenticate.tasks import check_credentials
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.service import Service


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('logging.Logger.error', MagicMock())
    monkeypatch.setattr('breathecode.notify.actions.send_email_message', MagicMock())

    yield


class ResponseMock:

    def __init__(self, data, status):
        self.status_code = status
        self.data = data

    def json(self):
        return self.data


@pytest.fixture
def patch_request(monkeypatch):

    def wrapper(data, status):
        monkeypatch.setattr('breathecode.utils.service.Service.get',
                            MagicMock(return_value=ResponseMock(data, status)))
        return MagicMock()

    yield wrapper


def test_nothing_to_check(bc: Breathecode):
    check_credentials.delay(1)

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == []

    assert logging.Logger.error.call_args_list == [
        call('Nothing to check', exc_info=True),
    ]


# you should parametrize these tests to check with another apps


def test_not_found(bc: Breathecode):
    check_credentials.delay(1, ['rigobot'])

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == []

    assert logging.Logger.error.call_args_list == [
        call('FirstPartyCredentials not found', exc_info=True),
    ]


def test_if_rigobot_id_is_null_remove_its_related_log(bc: Breathecode):
    with patch('breathecode.authenticate.tasks.check_credentials.delay', MagicMock()):
        model = bc.database.create(first_party_credentials={
            'rigobot_id': None,
            'health_status': {
                'rigobot': {
                    'random': 'value',
                },
            },
        })
    check_credentials.delay(1, ['rigobot'])

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
        {
            **bc.format.to_dict(model.first_party_credentials),
            'health_status': {},
        },
    ]

    assert logging.Logger.error.call_args_list == []


def test_app_not_found(bc: Breathecode):
    with patch('breathecode.authenticate.tasks.check_credentials.delay', MagicMock()):
        model = bc.database.create(first_party_credentials={'rigobot_id': 1})
    check_credentials.delay(1, ['rigobot'])

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
        bc.format.to_dict(model.first_party_credentials),
    ]

    assert logging.Logger.error.call_args_list == [
        call('App not found', exc_info=True),
    ]


@pytest.mark.parametrize('status,data', [(404, []), (200, {}), (200, [])])
def test_not_found_on_rigobot(bc: Breathecode, patch_request, status, data):
    patch_request(data, status)
    id = random.randint(1, 100)

    with patch('breathecode.authenticate.tasks.check_credentials.delay', MagicMock()):
        model = bc.database.create(first_party_credentials={'rigobot_id': id}, app={'slug': 'rigobot'})

    check_credentials.delay(1, ['rigobot'])

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
        {
            **bc.format.to_dict(model.first_party_credentials),
            'health_status': {
                'rigobot': {
                    'id': id,
                    'status': 'NOT_FOUND',
                },
            },
            'rigobot_id': None,
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert Service.get.call_args_list == [
        call(f'/v1/auth/app/user/?email={model.user.email}&id={id}'),
    ]


def test_found_on_rigobot(bc: Breathecode, patch_request):
    patch_request([1], 200)
    id = random.randint(1, 100)

    with patch('breathecode.authenticate.tasks.check_credentials.delay', MagicMock()):
        model = bc.database.create(first_party_credentials={'rigobot_id': id}, app={'slug': 'rigobot'})

    check_credentials.delay(1, ['rigobot'])

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
        {
            **bc.format.to_dict(model.first_party_credentials),
            'health_status': {
                'rigobot': {
                    'id': id,
                    'status': 'HEALTHY',
                },
            },
            'rigobot_id': id,
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert Service.get.call_args_list == [
        call(f'/v1/auth/app/user/?email={model.user.email}&id={id}'),
    ]


# def test_bad_fields(bc: Breathecode):
#     model = bc.database.create(first_party_webhook_log=1)

#     import_external_user.delay(1)

#     assert bc.database.list_of('authenticate.FirstPartyCredentials') == []
#     assert bc.database.list_of('auth.User') == []

#     assert logging.Logger.error.call_args_list == [
#         call('Webhook unknown requires a data field as json with the following '
#              'fields: data.id, data.email, data.first_name, data.last_name'),
#     ]
#     assert check_credentials.delay.call_args_list == []

# def test_user_created(bc: Breathecode, fake):
#     id = random.randint(1, 100)
#     email = fake.email()
#     first_name = fake.first_name()
#     last_name = fake.last_name()
#     model = bc.database.create(first_party_webhook_log={
#         'data': {
#             'id': id,
#             'email': email,
#             'first_name': first_name,
#             'last_name': last_name,
#         },
#         'user_id': 1,
#     })

#     import_external_user.delay(1)

#     assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
#         {
#             'health_status': {},
#             'id': 1,
#             'rigobot_id': id,
#             'user_id': 1,
#         },
#     ]
#     db = [x for x in bc.database.list_of('auth.User') if isinstance(x.pop('date_joined'), datetime)]
#     assert db == [
#         {
#             'email': email,
#             'first_name': first_name,
#             'id': 1,
#             'is_active': True,
#             'is_staff': False,
#             'is_superuser': False,
#             'last_login': None,
#             'last_name': last_name,
#             'password': '',
#             'username': email,
#         },
#     ]

#     assert logging.Logger.error.call_args_list == []
#     assert check_credentials.delay.call_args_list == [call(1, ['rigobot'])]
