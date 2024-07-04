import gzip
import json
import os
import random
import re
from unittest.mock import MagicMock, call

import brotli
import django.contrib.auth.models as auth_models
import pytest
from django.core.cache import cache

import breathecode.admissions.models as admissions_models
import breathecode.assignments.models as assignment_models
import breathecode.authenticate.models as authenticate_models
import breathecode.certificate.models as certificate_models
import breathecode.events.models as event_models
import breathecode.events.models as events_models
import breathecode.feedback.models as feedback_models
import breathecode.marketing.models as marketing_models
import breathecode.notify.models as notify_models
import breathecode.payments.models as payments_models
import breathecode.provisioning.models as provisioning_models
from breathecode.admissions.caches import CohortCache
from breathecode.events.caches import EventCache
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.cache import CACHE_DESCRIPTORS, Cache

# this fix a problem caused by the geniuses at pytest-xdist
random.seed(os.getenv("RANDOM_SEED"))

cohort_cache = CohortCache()
event_cache = EventCache()

CACHE = {"Cohort": CohortCache, "Event": EventCache}


def to_snake_case(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


@pytest.fixture(autouse=True)
def setup(db):
    yield


def set_cache(model_name, value):
    json_data = json.dumps(value).encode("utf-8")

    cache.set(f"{model_name}__", json_data)
    cache.set(f"{model_name}__sort=slug&slug=100%2C101%2C110%2C111", json_data)
    cache.set(f"{model_name}__id=1", json_data)
    cache.set(f"{model_name}__id=2", json_data)
    cache.set(
        f"{model_name}__keys",
        {
            f"{model_name}__",
            f"{model_name}__id=1",
            f"{model_name}__id=2",
            f"{model_name}__sort=slug&slug=100%2C101%2C110%2C111",
        },
    )


def assert_cache_is_empty(model_name):
    assert CACHE[model_name].keys() == set()

    assert cache.get(f"{model_name}__") == None
    assert cache.get(f"{model_name}__sort=slug&slug=100%2C101%2C110%2C111") == None
    assert cache.get(f"{model_name}__id=1") == None
    assert cache.get(f"{model_name}__id=2") == None


@pytest.mark.parametrize("model_name,key,value", [("Cohort", "name", "x"), ("Event", "title", "y")])
@pytest.mark.parametrize("expected", [[], [{"x": 1}], [{"x": 1}, {"x": 2}]])
def test_create_update_and_delete(bc: Breathecode, enable_signals, model_name, key, value, expected):
    enable_signals(
        "django.db.models.signals.post_save",
        "django.db.models.signals.post_delete",
        "breathecode.commons.signals.update_cache",
    )

    attr = to_snake_case(model_name)

    lookups = {attr: 1}
    model = bc.database.create(**lookups)

    set_cache(model_name, expected)

    # update
    x = getattr(model, attr)
    setattr(x, key, value)
    x.save()

    assert_cache_is_empty(model_name)

    set_cache(model_name, expected)

    # delete
    getattr(model, attr).delete()

    CACHE[model_name].keys() == []

    assert_cache_is_empty(model_name)


def test_cache_defaults():
    assert Cache.max_deep == 2


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
def test_model_cache(cache_cls):
    assert cache_cls.max_deep == 2


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
def test_cache_as_dependency_is_false(cache_cls):
    assert cache_cls.is_dependency == False


@pytest.mark.parametrize(
    "cache_cls,value",
    [
        (
            CohortCache,
            set(
                [
                    notify_models.SlackChannel,
                ]
            ),
        ),
        (EventCache, set([])),
    ],
)
def test_model_cache__one_to_one(cache_cls, value):
    assert cache_cls.one_to_one == value


@pytest.mark.parametrize(
    "cache_cls,value",
    [
        (
            CohortCache,
            set(
                [
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
                ]
            ),
        ),
        (
            EventCache,
            set(
                [
                    auth_models.User,
                    events_models.EventbriteWebhook,
                    events_models.Organization,
                    events_models.EventType,
                    events_models.EventCheckin,
                    events_models.Venue,
                    admissions_models.Academy,
                    feedback_models.Answer,
                ]
            ),
        ),
    ],
)
def test_model_cache__many_to_one(cache_cls, value):
    assert cache_cls.many_to_one == value


@pytest.mark.parametrize(
    "cache_cls,value",
    [
        (
            CohortCache,
            set(
                [
                    payments_models.CohortSet,
                    payments_models.PlanFinancing,
                    payments_models.Subscription,
                    payments_models.SubscriptionServiceItem,
                    provisioning_models.ProvisioningProfile,
                ]
            ),
        ),
        (EventCache, set()),
    ],
)
def test_model_cache__many_to_many(cache_cls, value):
    assert cache_cls.many_to_many == value


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key",
    [
        (
            [],
            {},
            "",
        ),
        (
            [{"x": 1}],
            {"x": 1},
            "x=1",
        ),
        (
            [{"x": 1}, {"y": 2}],
            {"x": 1, "y": 2},
            "x=1&y=2",
        ),
    ],
)
def test_set_cache(cache_cls: Cache, value, params, key):
    res = cache_cls.set(value, params=params)

    serialized = json.dumps(value).encode("utf-8")
    assert res == {
        "content": serialized,
        "headers": {
            "Content-Type": "application/json",
        },
    }

    keys = f"{cache_cls.model.__name__}__keys"
    k = f"{cache_cls.model.__name__}__{key}"
    assert sorted(cache.keys()) == sorted([keys, k])
    assert cache_cls.keys() == {k}

    assert cache.get(k) == res


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key",
    [
        (
            [],
            {},
            "",
        ),
        (
            [
                {"x": 1},
            ],
            {"x": 1},
            "x=1",
        ),
        (
            [
                {"x": 1},
                {"y": 2},
            ],
            {"x": 1, "y": 2},
            "x=1&y=2",
        ),
    ],
)
def test_set_cache_compressed(monkeypatch, cache_cls: Cache, value, params, key):
    monkeypatch.setattr("sys.getsizeof", lambda _: (random.randint(10, 1000) * 1024) + 1)

    res = cache_cls.set(value, params=params, encoding="br")

    serialized = brotli.compress(json.dumps(value).encode("utf-8"))
    assert res == {
        "content": serialized,
        "headers": {
            "Content-Encoding": "br",
            "Content-Type": "application/json",
        },
    }

    keys = f"{cache_cls.model.__name__}__keys"
    k = f"{cache_cls.model.__name__}__{key}"
    assert sorted(cache.keys()) == sorted([k, keys])
    assert cache_cls.keys() == {k}

    assert cache.get(k) == res


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key",
    [
        (
            [],
            {},
            "",
        ),
        (
            [
                {"x": 1},
            ],
            {"x": 1},
            "x=1",
        ),
        (
            [
                {"x": 1},
                {"y": 2},
            ],
            {"x": 1, "y": 2},
            "x=1&y=2",
        ),
    ],
)
@pytest.mark.parametrize("use_gzip,encoding", [(True, "br"), (False, "gzip"), (True, "gzip")])
def test_set_cache_compressed__gzip(monkeypatch, cache_cls: Cache, value, params, key, use_gzip, encoding):
    monkeypatch.setattr("sys.getsizeof", lambda _: (random.randint(10, 1000) * 1024) + 1)
    monkeypatch.setattr("breathecode.utils.cache.use_gzip", lambda: use_gzip)

    res = cache_cls.set(value, params=params, encoding=encoding)

    serialized = gzip.compress(json.dumps(value).encode("utf-8"))
    assert res == {
        "content": serialized,
        "headers": {
            "Content-Encoding": "gzip",
            "Content-Type": "application/json",
        },
    }

    keys = f"{cache_cls.model.__name__}__keys"
    k = f"{cache_cls.model.__name__}__{key}"
    assert sorted(cache.keys()) == sorted([k, keys])
    assert cache_cls.keys() == {k}

    assert cache.get(k) == res


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key,headers",
    [
        (
            [],
            {},
            "",
            {
                "Content-Type": "application/json",
            },
        ),
        (
            [{"x": 1}],
            {"x": 1},
            "x=1",
            {
                "Content-Type": "application/json",
            },
        ),
        (
            [{"x": 1}, {"y": 2}],
            {"x": 1, "y": 2},
            "x=1&y=2",
            {
                "Content-Type": "application/json",
            },
        ),
    ],
)
def test_get_cache__with_meta(cache_cls: Cache, value, params, key, headers):
    k = f"{cache_cls.model.__name__}__{key}"
    serialized = json.dumps(value).encode("utf-8")
    res = {
        "headers": headers,
        "content": serialized,
    }
    cache.set(k, res)

    assert cache_cls.get(params) == (serialized, headers)


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key,headers",
    [
        (
            [],
            {},
            "",
            {
                "Content-Encoding": "br",
                "Content-Type": "application/json",
            },
        ),
        (
            [
                {"x": 1},
            ],
            {"x": 1},
            "x=1",
            {
                "Content-Encoding": "br",
                "Content-Type": "application/json",
            },
        ),
        (
            [
                {"x": 1},
                {"y": 2},
            ],
            {"x": 1, "y": 2},
            "x=1&y=2",
            {
                "Content-Encoding": "br",
                "Content-Type": "application/json",
            },
        ),
    ],
)
def test_get_cache_compressed__with_meta(cache_cls: Cache, value, params, key, headers):
    k = f"{cache_cls.model.__name__}__{key}"
    v = json.dumps(value).encode("utf-8")
    serialized = brotli.compress(v)

    res = {
        "headers": headers,
        "content": serialized,
    }
    cache.set(k, res)

    assert cache_cls.get(params) == (serialized, headers)


@pytest.mark.parametrize("cache_cls", [CohortCache, EventCache])
@pytest.mark.parametrize(
    "value,params,key,headers",
    [
        (
            [],
            {},
            "",
            {
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        ),
        (
            [
                {"x": 1},
            ],
            {"x": 1},
            "x=1",
            {
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        ),
        (
            [
                {"x": 1},
                {"y": 2},
            ],
            {"x": 1, "y": 2},
            "x=1&y=2",
            {
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        ),
    ],
)
def test_get_cache_compressed__with_meta__gzip(monkeypatch, cache_cls: Cache, value, params, key, headers):
    monkeypatch.setattr("breathecode.utils.cache.use_gzip", lambda: True)

    k = f"{cache_cls.model.__name__}__{key}"
    v = json.dumps(value).encode("utf-8")
    serialized = gzip.compress(v)

    res = {
        "headers": headers,
        "content": serialized,
    }
    cache.set(k, res)

    assert cache_cls.get(params) == (serialized, headers)


@pytest.mark.parametrize(
    "cache_cls,calls",
    [
        (
            CohortCache,
            [
                "Cohort__",
                "Answer__",
                "CohortSetCohort__",
                "CohortSet__",
                "CohortTimeSlot__",
                "CohortUser__",
                "Course__",
                "EventTypeVisibilitySetting__",
                "FinalProject__",
                "GitpodUser__",
                "PlanFinancing__",
                "ProvisioningProfile__",
                "SyllabusVersion__",
                "Academy__",
                "Review__",
                "SlackChannel__",
                "SubscriptionServiceItem__",
                "Subscription__",
                "Survey__",
                "SyllabusSchedule__",
                "Task__",
                "UserInvite__",
                "UserSpecialty__",
            ],
        ),
        (
            EventCache,
            [
                "Event__",
                "Answer__",
                "EventCheckin__",
                "EventType__",
                "User__",
                "EventbriteWebhook__",
                "Organization__",
                "Academy__",
                "Venue__",
            ],
        ),
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        [],
        [
            {"x": 1},
        ],
        [
            {"x": 1},
            {"y": 2},
        ],
    ],
)
def test_delete_calls(faker, monkeypatch, cache_cls: Cache, calls, value):
    mock = MagicMock()
    monkeypatch.setattr("breathecode.settings.CustomMemCache.delete_many", mock)

    keys = set()
    for c in calls:
        index = f"{c}keys"
        keys.add(f"{c}keys")

        inner = set()

        for _ in range(0, 3):
            k = f"{c}{faker.slug()}"
            keys.add(k)
            inner.add(k)

        cache.set(index, inner)

    k = f"{cache_cls.model.__name__}__"
    serialized = json.dumps(value).encode("utf-8")
    cache.set(k, serialized)

    cache_cls.clear()

    assert sorted(mock.call_args_list) == [call(set(sorted({c for c in keys})))]
