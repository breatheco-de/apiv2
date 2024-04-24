import random
from datetime import datetime, timedelta, timezone

import pytest
from django.urls import reverse_lazy
from rest_framework import status

from bc.rest_framework.pytest import fixtures as rfx
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr('breathecode.payments.tasks.end_the_consumption_session.apply_async',
                        lambda *args, **kwargs: None)
    yield


def random_duration():
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def db_item(service, data={}):
    return {
        'consumable_id': 1,
        'duration': ...,
        'eta': ...,
        'how_many': 1.0,
        'id': 1,
        'operation_code': 'unsafe-consume-service-set',
        'path': '',
        'related_id': 0,
        'related_slug': '',
        'request': {
            'args': [],
            'headers': {
                'academy': None,
            },
            'kwargs': {
                'hash': '1234567890123456',
                'service_slug': service.slug,
            },
            'user': 1,
        },
        'status': 'PENDING',
        'user_id': 1,
        'was_discounted': False,
        **data,
    }


def test_no_auth(bc: Breathecode, client: rfx.Client):
    url = reverse_lazy('payments:me_service_slug_cancel_hash',
                       kwargs={
                           'service_slug': 'my-service',
                           'hash': '1234567890123456'
                       })

    response = client.put(url)

    json = response.json()
    expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of('payments.ConsumptionSession') == []


@pytest.mark.parametrize('with_session', [False, True])
def test_no_sessions(bc: Breathecode, client: rfx.Client, with_session, fake, utc_now):
    slug = fake.slug()
    duration = random_duration()
    url = reverse_lazy('payments:me_service_slug_cancel_hash',
                       kwargs={
                           'service_slug': 'my-service',
                           'hash': '1234567890123456'
                       })
    extra = {}

    if with_session:
        extra.update({
            'consumable': 1,
            'service': {
                'session_duration': duration,
                'slug': slug,
            },
            'service_set': 1,
            'consumption_session': {
                'how_many': 1,
                'eta': utc_now + duration,
                'duration': duration,
                'was_discounted': False,
                'operation_code': 'unsafe-consume-service-set',
                'related_id': 0,
                'related_slug': '',
                'status': 'CANCELLED',
                'path': '',
                'request': {
                    'args': [],
                    'headers': {
                        'academy': None,
                    },
                    'kwargs': {
                        'hash': '1234567890123456',
                        'service_slug': slug,
                    },
                    'user': 1,
                },
            },
        })

    model = bc.database.create(user=1, **extra)
    client.force_authenticate(user=model.user)

    response = client.put(url)

    json = response.json()
    expected = {'detail': 'session-not-found', 'status_code': 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    if with_session:
        assert bc.database.list_of('payments.ConsumptionSession') == [bc.format.to_dict(model.consumption_session)]
    else:
        assert bc.database.list_of('payments.ConsumptionSession') == []


def test_cancelled(bc: Breathecode, client: rfx.Client, utc_now, fake):
    slug = fake.slug()
    duration = random_duration()
    model = bc.database.create(user=1,
                               consumable=1,
                               service={
                                   'session_duration': duration,
                                   'slug': slug,
                               },
                               service_set=1,
                               consumption_session={
                                   'how_many': 1,
                                   'eta': utc_now + duration,
                                   'duration': duration,
                                   'was_discounted': False,
                                   'operation_code': 'unsafe-consume-service-set',
                                   'related_id': 0,
                                   'related_slug': '',
                                   'status': 'PENDING',
                                   'path': '',
                                   'request': {
                                       'args': [],
                                       'headers': {
                                           'academy': None,
                                       },
                                       'kwargs': {
                                           'hash': '1234567890123456',
                                           'service_slug': slug,
                                       },
                                       'user': 1,
                                   },
                               })
    url = reverse_lazy('payments:me_service_slug_cancel_hash',
                       kwargs={
                           'service_slug': model.service.slug,
                           'hash': '1234567890123456'
                       })

    client.force_authenticate(user=model.user)

    response = client.put(url)

    json = response.json()
    expected = {'status': 'reversed'}

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of('payments.ConsumptionSession') == [
        db_item(model.service, data={
            'duration': duration,
            'eta': utc_now + duration,
        })
    ]
