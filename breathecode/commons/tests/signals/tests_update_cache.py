import os
import random
import re
import json
from unittest.mock import MagicMock, call
from django.core.cache import cache
import pytest
from breathecode.admissions.caches import CohortCache
from breathecode.events.caches import EventCache
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.cache import CACHE_DESCRIPTORS, Cache
import brotli

import django.contrib.auth.models as auth_models
import breathecode.assignments.models as assignment_models
import breathecode.events.models as event_models
import breathecode.admissions.models as admissions_models
import breathecode.certificate.models as certificate_models
import breathecode.payments.models as payments_models
import breathecode.marketing.models as marketing_models
import breathecode.feedback.models as feedback_models
import breathecode.provisioning.models as provisioning_models
import breathecode.authenticate.models as authenticate_models
import breathecode.events.models as events_models
import breathecode.notify.models as notify_models

# this fix a problem caused by the geniuses at pytest-xdist
random.seed(os.getenv('RANDOM_SEED'))

cohort_cache = CohortCache()
event_cache = EventCache()

CACHE = {'Cohort': CohortCache, 'Event': EventCache}


def to_snake_case(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def set_cache(model_name, value):
    json_data = json.dumps(value).encode('utf-8')

    cache.set(f'{model_name}__', json_data)
    cache.set(f'{model_name}__sort=slug&slug=100%2C101%2C110%2C111', json_data)
    cache.set(f'{model_name}__id=1', json_data)
    cache.set(f'{model_name}__id=2', json_data)


def assert_cache_is_empty(model_name):
    assert CACHE[model_name].keys() == []

    assert cache.get(f'{model_name}__') == None
    assert cache.get(f'{model_name}__sort=slug&slug=100%2C101%2C110%2C111') == None
    assert cache.get(f'{model_name}__id=1') == None
    assert cache.get(f'{model_name}__id=2') == None


@pytest.mark.parametrize('model_name,key,value', [('Cohort', 'name', 'x'), ('Event', 'title', 'y')])
@pytest.mark.parametrize('expected', [[], [{'x': 1}], [{'x': 1}, {'x': 2}]])
def test_create_update_and_delete(bc: Breathecode, enable_signals, model_name, key, value, expected):
    enable_signals(
        'django.db.models.signals.post_save',
        'django.db.models.signals.post_delete',
        'breathecode.commons.signals.update_cache',
    )

    attr = to_snake_case(model_name)

    lookups = {attr: 1}
    model = bc.database.create(**lookups)

    set_cache(model_name, expected)

    # update
    x = getattr(model, attr)
    setattr(x, key, value)
    x.save()

    CACHE[model_name].keys() == []

    assert_cache_is_empty(model_name)

    set_cache(model_name, expected)

    # delete
    getattr(model, attr).delete()

    CACHE[model_name].keys() == []

    assert_cache_is_empty(model_name)


def test_cache_defaults():
    assert Cache.max_deep == 2


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
def test_model_cache(cache_cls):
    assert cache_cls.max_deep == 2


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
def test_cache_as_dependency_is_false(cache_cls):
    assert cache_cls.is_dependency == False


@pytest.mark.parametrize('cache_cls,value', [
    (CohortCache, set([
        notify_models.SlackChannel,
    ])),
    (EventCache, set([])),
])
def test_model_cache__one_to_one(cache_cls, value):
    assert cache_cls.one_to_one == value


@pytest.mark.parametrize('cache_cls,value', [
    (CohortCache,
     set([
         admissions_models.Academy,
         admissions_models.SyllabusVersion,
         admissions_models.SyllabusSchedule,
         admissions_models.CohortUser,
         admissions_models.CohortTimeSlot,
         authenticate_models.UserInvite,
         authenticate_models.GitpodUser,
         events_models.EventTypeVisibilitySetting,
         feedback_models.Review,
         feedback_models.Survey,
         feedback_models.Answer,
         assignment_models.Task,
         assignment_models.FinalProject,
         marketing_models.Course,
         certificate_models.UserSpecialty,
         payments_models.CohortSet,
         payments_models.CohortSetCohort,
         payments_models.PlanFinancing,
         payments_models.Subscription,
         payments_models.SubscriptionServiceItem,
         provisioning_models.ProvisioningProfile,
     ])),
    (EventCache,
     set([
         auth_models.User,
         events_models.EventbriteWebhook,
         events_models.Organization,
         events_models.EventType,
         events_models.EventCheckin,
         events_models.Venue,
         admissions_models.Academy,
         feedback_models.Answer,
     ])),
])
def test_model_cache__many_to_one(cache_cls, value):
    assert cache_cls.many_to_one == value


@pytest.mark.parametrize('cache_cls,value', [
    (CohortCache,
     set([
         payments_models.CohortSet,
         payments_models.PlanFinancing,
         payments_models.Subscription,
         payments_models.SubscriptionServiceItem,
         provisioning_models.ProvisioningProfile,
     ])),
    (EventCache, set()),
])
def test_model_cache__many_to_many(cache_cls, value):
    assert cache_cls.many_to_many == value


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key', [
    (
        [],
        {},
        '',
    ),
    (
        [{
            'x': 1
        }],
        {
            'x': 1
        },
        'x=1',
    ),
    (
        [{
            'x': 1
        }, {
            'y': 2
        }],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
    ),
])
def test_set_cache(cache_cls: Cache, value, params, key):
    cache_cls.set(value, params=params)

    k = f'{cache_cls.model.__name__}__{key}'
    assert cache.keys() == [k]
    assert cache_cls.keys() == [k]

    assert cache.get(k) == b'application/json    ' + json.dumps(value).encode('utf-8')


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key', [
    (
        [],
        {},
        '',
    ),
    (
        [
            {
                'x': 1
            },
        ],
        {
            'x': 1
        },
        'x=1',
    ),
    (
        [
            {
                'x': 1
            },
            {
                'y': 2
            },
        ],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
    ),
])
def test_set_cache_compressed(monkeypatch, cache_cls: Cache, value, params, key):
    monkeypatch.setattr('sys.getsizeof', lambda _: (random.randint(10, 1000) * 1024) + 1)

    cache_cls.set(value, params=params)

    k = f'{cache_cls.model.__name__}__{key}'
    assert cache.keys() == [k]
    assert cache_cls.keys() == [k]

    assert cache.get(k) == b'application/json:br    ' + brotli.compress(json.dumps(value).encode('utf-8'))


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key,headers', [
    (
        [],
        {},
        '',
        {},
    ),
    (
        [{
            'x': 1
        }],
        {
            'x': 1
        },
        'x=1',
        {},
    ),
    (
        [{
            'x': 1
        }, {
            'y': 2
        }],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
        {},
    ),
])
def test_get_cache__no_meta(cache_cls: Cache, value, params, key, headers):
    k = f'{cache_cls.model.__name__}__{key}'
    serialized = json.dumps(value).encode('utf-8')
    cache.set(k, serialized)

    assert cache_cls.get(params) == (serialized, 'application/json', headers)


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key,headers', [
    (
        [],
        {},
        '',
        {},
    ),
    (
        [{
            'x': 1
        }],
        {
            'x': 1
        },
        'x=1',
        {},
    ),
    (
        [{
            'x': 1
        }, {
            'y': 2
        }],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
        {},
    ),
])
def test_get_cache__with_meta(cache_cls: Cache, value, params, key, headers):
    k = f'{cache_cls.model.__name__}__{key}'
    serialized = json.dumps(value).encode('utf-8')
    cache.set(k, b'application/json    ' + serialized)

    assert cache_cls.get(params) == (serialized, 'application/json', headers)


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key,headers', [
    (
        [],
        {},
        '',
        {
            'Content-Encoding': 'br',
        },
    ),
    (
        [
            {
                'x': 1
            },
        ],
        {
            'x': 1
        },
        'x=1',
        {
            'Content-Encoding': 'br',
        },
    ),
    (
        [
            {
                'x': 1
            },
            {
                'y': 2
            },
        ],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
        {
            'Content-Encoding': 'br',
        },
    ),
])
def test_get_cache_compressed__no_meta(cache_cls: Cache, value, params, key, headers):

    k = f'{cache_cls.model.__name__}__{key}'
    v = json.dumps(value).encode('utf-8')
    serialized = brotli.compress(v)
    cache.set(k, serialized)

    assert cache_cls.get(params) == (serialized, 'application/json', headers)


@pytest.mark.parametrize('cache_cls', [CohortCache, EventCache])
@pytest.mark.parametrize('value,params,key,headers', [
    (
        [],
        {},
        '',
        {
            'Content-Encoding': 'br',
        },
    ),
    (
        [
            {
                'x': 1
            },
        ],
        {
            'x': 1
        },
        'x=1',
        {
            'Content-Encoding': 'br',
        },
    ),
    (
        [
            {
                'x': 1
            },
            {
                'y': 2
            },
        ],
        {
            'x': 1,
            'y': 2
        },
        'x=1&y=2',
        {
            'Content-Encoding': 'br',
        },
    ),
])
def test_get_cache_compressed__with_meta(cache_cls: Cache, value, params, key, headers):
    k = f'{cache_cls.model.__name__}__{key}'
    v = json.dumps(value).encode('utf-8')
    serialized = brotli.compress(v)
    cache.set(k, b'application/json:br    ' + serialized)

    assert cache_cls.get(params) == (serialized, 'application/json', headers)


@pytest.mark.parametrize('cache_cls,calls', [
    (CohortCache, [
        call('Cohort__*'),
        call('Answer__*'),
        call('CohortSetCohort__*'),
        call('CohortSet__*'),
        call('CohortTimeSlot__*'),
        call('CohortUser__*'),
        call('Course__*'),
        call('EventTypeVisibilitySetting__*'),
        call('FinalProject__*'),
        call('GitpodUser__*'),
        call('PlanFinancing__*'),
        call('ProvisioningProfile__*'),
        call('SyllabusVersion__*'),
        call('Academy__*'),
        call('Review__*'),
        call('SlackChannel__*'),
        call('SubscriptionServiceItem__*'),
        call('Subscription__*'),
        call('Survey__*'),
        call('SyllabusSchedule__*'),
        call('Task__*'),
        call('UserInvite__*'),
        call('UserSpecialty__*'),
    ]),
    (EventCache, [
        call('Event__*'),
        call('Answer__*'),
        call('EventCheckin__*'),
        call('EventType__*'),
        call('User__*'),
        call('EventbriteWebhook__*'),
        call('Organization__*'),
        call('Academy__*'),
        call('Venue__*'),
    ]),
])
@pytest.mark.parametrize('value', [
    [],
    [
        {
            'x': 1
        },
    ],
    [
        {
            'x': 1
        },
        {
            'y': 2
        },
    ],
])
def test_delete_calls(monkeypatch, cache_cls: Cache, calls, value):

    mock = MagicMock()
    monkeypatch.setattr('breathecode.settings.CustomMemCache.delete_pattern', mock)

    k = f'{cache_cls.model.__name__}__'
    serialized = json.dumps(value).encode('utf-8')
    cache.set(k, serialized)

    cache_cls.clear()

    assert sorted(mock.call_args_list) == sorted(calls)
