import logging
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from breathecode.authenticate.tasks import create_user_from_invite
from breathecode.notify import actions as notify_actions
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('logging.Logger.error', MagicMock())
    monkeypatch.setattr('breathecode.notify.actions.send_email_message', MagicMock())
    yield


def prepare(db: list[dict]):
    return [x for x in db if isinstance(x.pop('date_joined'), datetime)]


def user_serializer(data={}):
    return {
        'email': '',
        'first_name': '',
        'id': 1,
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'last_login': None,
        'last_name': '',
        'password': '',
        'username': '',
        **data,
    }


def test_no_invites(bc: Breathecode):
    create_user_from_invite.delay(1)

    assert bc.database.list_of('authenticate.UserInvite') == []
    assert bc.database.list_of('auth.User') == []

    assert logging.Logger.error.call_args_list == [call('User invite not found', exc_info=True)]


@pytest.mark.parametrize('status', ['PENDING', 'WAITING_LIST', 'REJECTED'])
def test_invite_not_accepted(bc: Breathecode, status):
    model = bc.database.create(user_invite={'status': status})

    create_user_from_invite.delay(1)

    assert bc.database.list_of('authenticate.UserInvite') == [bc.format.to_dict(model.user_invite)]
    assert bc.database.list_of('auth.User') == []

    assert logging.Logger.error.call_args_list == [call('User invite is not accepted', exc_info=True)]


def test_no_email(bc: Breathecode):
    model = bc.database.create(user_invite={'status': 'ACCEPTED'})

    create_user_from_invite.delay(1)

    assert bc.database.list_of('authenticate.UserInvite') == [bc.format.to_dict(model.user_invite)]
    assert bc.database.list_of('auth.User') == []

    assert logging.Logger.error.call_args_list == [call('No email found', exc_info=True)]


@pytest.mark.parametrize('is_linked_the_user', [True, False])
def test_user_exists(bc: Breathecode, fake, is_linked_the_user):
    email = fake.email()
    user = {'email': email}
    user_invite = {'status': 'ACCEPTED', 'email': email, 'user_id': None}
    if is_linked_the_user:
        user_invite['user_id'] = 1

    model = bc.database.create(user_invite=user_invite, user=user)

    create_user_from_invite.delay(1)

    assert bc.database.list_of('authenticate.UserInvite') == [
        {
            **bc.format.to_dict(model.user_invite),
            'user_id': 1,
        },
    ]
    assert bc.database.list_of('auth.User') == [bc.format.to_dict(model.user)]

    assert logging.Logger.error.call_args_list == [call('User invite is already associated to a user', exc_info=True)]


def test_invite_accepted(bc: Breathecode, fake):
    email = fake.email()
    user_invite = {'status': 'ACCEPTED', 'email': email, 'first_name': fake.first_name(), 'last_name': fake.last_name()}

    model = bc.database.create(user_invite=user_invite)

    create_user_from_invite.delay(1)

    assert bc.database.list_of('authenticate.UserInvite') == [bc.format.to_dict(model.user_invite)]

    del user_invite['status']
    user_invite['username'] = email

    assert prepare(bc.database.list_of('auth.User')) == [user_serializer({'id': 1, **user_invite})]

    assert logging.Logger.error.call_args_list == []
    assert notify_actions.send_email_message.call_args_list == [
        call('pick_password',
             email, {
                 'SUBJECT': 'Set your password at 4Geeks',
                 'LINK': '/v1/auth/password/' + model.user_invite.token
             },
             academy=None)
    ]
