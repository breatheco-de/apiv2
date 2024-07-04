import logging
import os
import pickle
import random
from typing import Optional
from unittest.mock import MagicMock, call

import pytest
import zstandard
from django.core.cache import cache
from django.utils import timezone
from google.cloud import bigquery

from breathecode.activity import actions
from breathecode.activity.management.commands.upload_activities import Command
from breathecode.activity.tasks import add_activity
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


def get_calls():
    utc_now = timezone.now()
    tomorrow = (utc_now + timezone.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(1, 25):
        cursor = tomorrow + timezone.timedelta(hours=i)
        yield call(args=(), eta=cursor)


class UUID4:

    def __init__(self, hash):
        self.hash = hash
        self.hex = hash

    def __str__(self):
        return self.hash


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch):
    v = 0

    def uuid4():
        nonlocal v
        v += 1
        return UUID4(f"c5d8cbc54a894dd0983caae1b850709{v}")

    m1 = MagicMock()
    m2 = MagicMock()
    m3 = MagicMock(return_value={})

    monkeypatch.setattr("logging.Logger.info", m1)
    monkeypatch.setattr("logging.Logger.error", m2)
    # monkeypatch.setattr('breathecode.services.google_cloud.credentials.resolve_credentials', lambda: None)
    monkeypatch.setattr("breathecode.activity.actions.get_activity_meta", m3)
    monkeypatch.setattr("django.utils.timezone.now", lambda: UTC_NOW)
    monkeypatch.setattr("uuid.uuid4", uuid4)
    monkeypatch.setattr("breathecode.activity.actions.get_workers_amount", lambda: 2)

    yield m1, m2, m3


@pytest.fixture
def set_activity_meta(monkeypatch):

    def wrapper(meta: Optional[dict] = None, exc: Optional[str] = None):
        if exc:
            m3 = MagicMock(side_effect=Exception(exc))
        else:
            m3 = MagicMock(return_value=meta)

        monkeypatch.setattr("breathecode.activity.actions.get_activity_meta", m3)
        return m3

    yield wrapper


@pytest.fixture
def decompress_and_parse():

    def wrapper(data: str):
        data = zstandard.decompress(data)
        data = pickle.loads(data)

        return data

    yield wrapper


def get_attrs_from_meta(meta: dict):
    for key in meta:
        yield {"key": key, "struct": "meta", "type": "STRING", "value": meta[key]}

    if not meta:
        return []


def test_type_and_no_id_or_slug(bc: Breathecode):
    kind = bc.fake.slug()

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User")

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == [
        call(
            "If related_type is provided, either related_id or related_slug must be provided, " "but not both.",
            exc_info=True,
        ),
    ]
    assert actions.get_activity_meta.call_args_list == []

    assert cache.get("activity:worker-0") is None


def test_type_with_id_and_slug(bc: Breathecode):
    kind = bc.fake.slug()

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_id=1, related_slug="slug")

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == [
        call("If related_type is not provided, both related_id and related_slug must also be absent.", exc_info=True),
    ]
    assert actions.get_activity_meta.call_args_list == []

    assert cache.get("activity:worker-0") is None


def test_adding_the_resource_with_id_and_no_meta(bc: Breathecode, decompress_and_parse):
    kind = bc.fake.slug()

    logging.Logger.info.call_args_list = []

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_id=1)

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == []

    assert actions.get_activity_meta.call_args_list == [call(kind, "auth.User", 1, None)]

    assert decompress_and_parse(cache.get("activity:worker-0")) == [
        {
            "data": {
                "id": "c5d8cbc54a894dd0983caae1b8507091",
                "user_id": 1,
                "kind": kind,
                "timestamp": UTC_NOW.isoformat(),
                "related": {
                    "type": "auth.User",
                    "slug": None,
                    "id": 1,
                },
                "meta": {},
            },
            "schema": [
                bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                bigquery.SchemaField(
                    "related",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[
                        bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                        bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    ],
                ),
                bigquery.SchemaField("meta", bigquery.enums.SqlTypeNames.STRUCT, "NULLABLE", fields=[]),
            ],
        },
    ]


def test_adding_the_resource_with_slug_and_no_meta(bc: Breathecode, decompress_and_parse):
    kind = bc.fake.slug()

    logging.Logger.info.call_args_list = []

    related_slug = bc.fake.slug()

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_slug=related_slug)

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == []

    assert actions.get_activity_meta.call_args_list == [call(kind, "auth.User", None, related_slug)]

    assert decompress_and_parse(cache.get("activity:worker-0")) == [
        {
            "data": {
                "id": "c5d8cbc54a894dd0983caae1b8507091",
                "user_id": 1,
                "kind": kind,
                "timestamp": UTC_NOW.isoformat(),
                "related": {
                    "type": "auth.User",
                    "slug": related_slug,
                    "id": None,
                },
                "meta": {},
            },
            "schema": [
                bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                bigquery.SchemaField(
                    "related",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[
                        bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                        bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    ],
                ),
                bigquery.SchemaField("meta", bigquery.enums.SqlTypeNames.STRUCT, "NULLABLE", fields=[]),
            ],
        },
    ]


def test_adding_the_resource_with_meta(bc: Breathecode, set_activity_meta, decompress_and_parse):
    kind = bc.fake.slug()

    meta = {
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
    }

    set_activity_meta(meta)

    logging.Logger.info.call_args_list = []

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_id=1)

    assert actions.get_activity_meta.call_args_list == [
        call(kind, "auth.User", 1, None),
    ]

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == []

    assert decompress_and_parse(cache.get("activity:worker-0")) == [
        {
            "data": {
                "id": "c5d8cbc54a894dd0983caae1b8507091",
                "user_id": 1,
                "kind": kind,
                "timestamp": UTC_NOW.isoformat(),
                "related": {
                    "type": "auth.User",
                    "slug": None,
                    "id": 1,
                },
                "meta": meta,
            },
            "schema": [
                bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                bigquery.SchemaField(
                    "related",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[
                        bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                        bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    ],
                ),
                bigquery.SchemaField(
                    "meta",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[bigquery.SchemaField(x, bigquery.enums.SqlTypeNames.STRING, "NULLABLE") for x in meta],
                ),
            ],
        },
    ]


def test_adding_the_resource_with_meta__it_fails(bc: Breathecode, set_activity_meta):
    kind = bc.fake.slug()

    exc = bc.fake.slug()

    logging.Logger.info.call_args_list = []

    set_activity_meta(exc=exc)

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_id=1)

    assert actions.get_activity_meta.call_args_list == [
        call(kind, "auth.User", 1, None),
    ]

    assert logging.Logger.info.call_args_list == [call(f"Executing add_activity related to {kind}")]
    assert logging.Logger.error.call_args_list == [call(exc, exc_info=True)]

    assert cache.get("activity:worker-0") is None


def test_adding_the_resource_with_meta__called_two_times(
    bc: Breathecode, monkeypatch, set_activity_meta, decompress_and_parse
):
    kind = bc.fake.slug()

    meta = {
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
        bc.fake.slug().replace("-", "_"): bc.fake.slug(),
    }

    set_activity_meta(meta)

    logging.Logger.info.call_args_list = []

    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid(), "created_at": timezone.now()}],
            1: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_id=1)
    cache.set(
        "workers",
        {
            0: [{"pid": os.getpid() + random.randint(1, 100), "created_at": timezone.now()}],
            1: [{"pid": os.getpid(), "created_at": timezone.now()}],
        },
    )

    add_activity.delay(1, kind, related_type="auth.User", related_id=1)
    assert logging.Logger.error.call_args_list == []

    assert actions.get_activity_meta.call_args_list == [
        call(kind, "auth.User", 1, None),
        call(kind, "auth.User", 1, None),
    ]

    assert logging.Logger.info.call_args_list == [
        call(f"Executing add_activity related to {kind}"),
        call(f"Executing add_activity related to {kind}"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert decompress_and_parse(cache.get("activity:worker-0")) == [
        {
            "data": {
                "id": "c5d8cbc54a894dd0983caae1b8507091",
                "user_id": 1,
                "kind": kind,
                "timestamp": UTC_NOW.isoformat(),
                "related": {
                    "type": "auth.User",
                    "slug": None,
                    "id": 1,
                },
                "meta": meta,
            },
            "schema": [
                bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                bigquery.SchemaField(
                    "related",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[
                        bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                        bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    ],
                ),
                bigquery.SchemaField(
                    "meta",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[bigquery.SchemaField(x, bigquery.enums.SqlTypeNames.STRING, "NULLABLE") for x in meta],
                ),
            ],
        },
    ]

    assert decompress_and_parse(cache.get("activity:worker-1")) == [
        {
            "data": {
                "id": "c5d8cbc54a894dd0983caae1b8507092",
                "user_id": 1,
                "kind": kind,
                "timestamp": UTC_NOW.isoformat(),
                "related": {
                    "type": "auth.User",
                    "slug": None,
                    "id": 1,
                },
                "meta": meta,
            },
            "schema": [
                bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                bigquery.SchemaField(
                    "related",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[
                        bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                        bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    ],
                ),
                bigquery.SchemaField(
                    "meta",
                    bigquery.enums.SqlTypeNames.STRUCT,
                    "NULLABLE",
                    fields=[bigquery.SchemaField(x, bigquery.enums.SqlTypeNames.STRING, "NULLABLE") for x in meta],
                ),
            ],
        },
    ]
