import logging
import random
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from breathecode.authenticate.tasks import check_credentials, import_external_user
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('logging.Logger.error', MagicMock())
    monkeypatch.setattr('breathecode.authenticate.tasks.check_credentials.delay', MagicMock())
    yield


def test_no_invites(bc: Breathecode):
    import_external_user.delay(1)

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == []
    assert bc.database.list_of('auth.User') == []

    assert logging.Logger.error.call_args_list == [
        call('Webhook not found', exc_info=True),
    ]
    assert check_credentials.delay.call_args_list == []


def test_bad_fields(bc: Breathecode):
    model = bc.database.create(first_party_webhook_log=1)

    import_external_user.delay(1)

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == []
    assert bc.database.list_of('auth.User') == []

    assert logging.Logger.error.call_args_list == [
        call('Webhook unknown requires a data field as json with the following '
             'fields: data.id, data.email, data.first_name, data.last_name'),
    ]
    assert check_credentials.delay.call_args_list == []


def test_user_created(bc: Breathecode, fake):
    id = random.randint(1, 100)
    email = fake.email()
    first_name = fake.first_name()
    last_name = fake.last_name()
    model = bc.database.create(first_party_webhook_log={
        'data': {
            'id': id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        },
        'user_id': 1,
    })

    import_external_user.delay(1)

    assert bc.database.list_of('authenticate.FirstPartyCredentials') == [
        {
            'health_status': {},
            'id': 1,
            'rigobot_id': id,
            'user_id': 1,
        },
    ]
    db = [x for x in bc.database.list_of('auth.User') if isinstance(x.pop('date_joined'), datetime)]
    assert db == [
        {
            'email': email,
            'first_name': first_name,
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': last_name,
            'password': '',
            'username': email,
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert check_credentials.delay.call_args_list == [call(1, ['rigobot'])]
