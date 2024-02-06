import random
from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.authenticate.management.commands.first_party_webhooks import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

T1 = timezone.now()


@pytest.fixture(autouse=True)
def patch(db, monkeypatch):
    # from breathecode.authenticate import tasks
    # return tasks.import_external_user.delay(webhook.id)
    m1 = MagicMock()

    monkeypatch.setattr('breathecode.authenticate.tasks.import_external_user.delay', m1)
    # monkeypatch.setattr('django.utils.timezone.now', lambda: T1)

    yield m1


@pytest.fixture
def freeze_time(monkeypatch):

    def wrapper(time=T1):
        monkeypatch.setattr('django.utils.timezone.now', lambda: time)

    yield wrapper


def test__nothing_to_migrate(bc: Breathecode, patch):
    import_external_user = patch
    command = Command()
    command.handle()

    assert bc.database.list_of('authenticate.FirstPartyWebhookLog') == []
    assert import_external_user.call_args_list == []


def test__no_calls__breathecode_log(bc: Breathecode, patch):
    model = bc.database.create(first_party_webhook_log=(2, {'attempts': 0}))
    import_external_user = patch
    command = Command()
    command.handle()

    db = bc.format.to_dict(model.first_party_webhook_log)
    assert bc.database.list_of('authenticate.FirstPartyWebhookLog') == db
    assert import_external_user.call_args_list == []


@pytest.mark.parametrize('delta,attempts', [
    (timedelta(0), 0),
    (timedelta(minutes=21), 1),
    (timedelta(minutes=22), 2),
    (timedelta(minutes=23), 3),
    (timedelta(minutes=24), 4),
    (timedelta(minutes=25), 5),
])
def test__no_calls__rigobot_requests(bc: Breathecode, patch, freeze_time, delta, attempts):
    import_external_user = patch

    model = bc.database.create(first_party_webhook_log=(2, {'attempts': attempts, 'external_id': 1}))

    freeze_time(T1 + delta)

    command = Command()
    command.handle()

    assert bc.database.list_of('authenticate.FirstPartyWebhookLog') == [
        {
            **bc.format.to_dict(model.first_party_webhook_log[0]),
            'status': 'ERROR',
            'status_text': 'Invalid webhook type',
        },
        {
            **bc.format.to_dict(model.first_party_webhook_log[1]),
            'status': 'ERROR',
            'status_text': 'Invalid webhook type',
        },
    ]
    assert import_external_user.call_args_list == []


@pytest.mark.parametrize('delta,attempts,type', [
    (timedelta(0), 0, 'user.created'),
    (timedelta(0), 0, 'user.updated'),
    (timedelta(minutes=21), 1, 'user.created'),
    (timedelta(minutes=22), 2, 'user.updated'),
    (timedelta(minutes=23), 3, 'user.created'),
    (timedelta(minutes=24), 4, 'user.updated'),
    (timedelta(minutes=25), 5, 'user.created'),
])
def test__user_events_scheduled(bc: Breathecode, patch, freeze_time, delta, attempts, type):
    import_external_user = patch

    model = bc.database.create(first_party_webhook_log=(2, {
        'attempts': attempts,
        'external_id': 1,
        'type': type
    }))

    freeze_time(T1 + delta)

    command = Command()
    command.handle()

    assert bc.database.list_of('authenticate.FirstPartyWebhookLog') == [
        {
            **bc.format.to_dict(model.first_party_webhook_log[0]),
            'status': 'PENDING',
        },
        {
            **bc.format.to_dict(model.first_party_webhook_log[1]),
            'status': 'PENDING',
        },
    ]
    assert import_external_user.call_args_list == [call(1), call(2)]
