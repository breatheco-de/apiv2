"""
Test /answer
"""

import pickle
import random
from unittest.mock import MagicMock, call

import pytest
import zstandard as zstd
from django.core.cache import cache
from django.utils import timezone
from google.cloud import bigquery
from google.cloud.bigquery.client import DatasetReference
from google.cloud.bigquery.table import TableReference

from breathecode.activity.tasks import upload_activities
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


class TableMock:

    def __init__(self, schema):
        self.schema = schema

    def __eq__(self, other):
        return self.schema == other.schema


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch):

    m1 = MagicMock()
    m2 = MagicMock()
    m3 = MagicMock()

    m3.return_value = TableMock(
        [
            bigquery.SchemaField("character", "STRING", "NULLABLE"),
            bigquery.SchemaField(
                "related",
                "RECORD",
                "NULLABLE",
                fields=(
                    bigquery.SchemaField("name", "STRING", "NULLABLE"),
                    bigquery.SchemaField("amount", "INT64", "NULLABLE"),
                ),
            ),
            bigquery.SchemaField(
                "meta",
                "RECORD",
                "NULLABLE",
                fields=(
                    bigquery.SchemaField("knife", "BOOL", "NULLABLE"),
                    bigquery.SchemaField("pistol", "FLOAT64", "NULLABLE"),
                ),
            ),
        ]
    )

    m4 = MagicMock()
    m5 = MagicMock(return_value=[])

    monkeypatch.setattr("logging.Logger.info", m1)
    monkeypatch.setattr("logging.Logger.error", m2)
    monkeypatch.setattr("breathecode.activity.actions.get_workers_amount", lambda: 2)
    monkeypatch.setattr("django.utils.timezone.now", lambda: UTC_NOW)
    monkeypatch.setattr("google.cloud.bigquery.Client.get_table", m3)
    monkeypatch.setattr("google.cloud.bigquery.Client.update_table", m4)
    monkeypatch.setattr("google.cloud.bigquery.Client.insert_rows", m5)

    monkeypatch.setattr("breathecode.services.google_cloud.credentials.resolve_credentials", lambda: None)

    monkeypatch.setenv("GOOGLE_PROJECT_ID", "project")
    monkeypatch.setenv("BIGQUERY_DATASET", "dataset")

    yield m1, m2, m3, m4, m5


@pytest.fixture
def get_schema():
    return lambda extra=[]: [
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
        *extra,
    ]


@pytest.fixture
def get_data(fake):
    return lambda data={}: {
        "id": fake.uuid4(),
        "user_id": random.randint(1, 100),
        "kind": fake.slug(),
        "timestamp": UTC_NOW.isoformat(),
        "related": {
            "type": f"{fake.slug()}.{fake.slug()}",
            "slug": fake.slug(),
            "id": random.randint(1, 100),
        },
        "meta": {},
        **data,
    }


def set_cache(key, value, timeout=None):
    data = pickle.dumps(value)
    data = zstd.compress(data)

    cache.set(key, data, timeout=timeout)


def get_cache(key):
    data = cache.get(key)

    if data is None:
        return None

    data = zstd.decompress(data)
    data = pickle.loads(data)

    return data


def sort_schema(table):
    schema = sorted(table.schema, key=lambda v: v.name)

    for field in schema:
        if field.field_type == "RECORD":
            field._fields = sorted(field._fields, key=lambda v: v.name)

    return schema


def both_schema_are_equal(a, b):
    assert len(a) == len(b)

    for i in range(len(a)):
        assert len(a[i].args) == len(b[i].args)

        assert sort_schema(a[i].args[0]) == sort_schema(b[i].args[0])

        assert a[i].args[1] == b[i].args[1]
        assert a[i].kwargs == b[i].kwargs


def test_no_data(bc: Breathecode, apply_patch):
    info_mock, error_mock, get_table_mock, update_table_mock, insert_rows_mock = apply_patch

    upload_activities.delay()

    assert info_mock.call_args_list == []
    assert error_mock.call_args_list == [call("No data to upload", exc_info=True)]

    assert get_cache("activity:worker-0") == None
    assert get_cache("activity:worker-1") == None

    task = bc.database.get("task_manager.TaskManager", 1, dict=False)

    assert get_cache(f"activity:backup:{task.id}") == None

    assert get_table_mock.call_args_list == []
    assert update_table_mock.call_args_list == []
    assert insert_rows_mock.call_args_list == []


def test_with_data_in_both_workers(bc: Breathecode, fake, apply_patch, get_schema, get_data):
    info_mock, error_mock, get_table_mock, update_table_mock, insert_rows_mock = apply_patch

    attr1 = fake.slug()
    attr2 = fake.slug()
    attr3 = fake.slug()
    attr4 = fake.slug()

    schema1 = get_schema(
        [
            bigquery.SchemaField(
                "meta",
                bigquery.enums.SqlTypeNames.STRUCT,
                "NULLABLE",
                fields=[
                    bigquery.SchemaField(attr1, bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                ],
            ),
        ]
    )

    schema2 = get_schema(
        [
            bigquery.SchemaField(
                "meta",
                bigquery.enums.SqlTypeNames.STRUCT,
                "NULLABLE",
                fields=[
                    bigquery.SchemaField(attr2, bigquery.enums.SqlTypeNames.BOOL, "NULLABLE"),
                    bigquery.SchemaField(attr3, bigquery.enums.SqlTypeNames.FLOAT64, "NULLABLE"),
                    bigquery.SchemaField(attr4, bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                ],
            ),
        ]
    )

    data1 = get_data({"meta": {attr1: 1}})
    data2 = get_data(
        {
            "meta": {
                attr2: bool(random.randint(0, 1)),
                attr3: random.random() * 100,
                attr4: random.randint(1, 100),
            },
        }
    )

    data3 = get_data(
        {
            "meta": {
                attr2: bool(random.randint(0, 1)),
                attr3: random.random() * 100,
                attr4: random.randint(1, 100),
            },
        }
    )

    set_cache(
        "activity:worker-0",
        [
            {
                "data": data1,
                "schema": schema1,
            },
        ],
    )

    set_cache(
        "activity:worker-1",
        [
            {
                "data": data2,
                "schema": schema2,
            },
            {
                "data": data3,
                "schema": schema2,
            },
        ],
    )

    upload_activities.delay()

    assert info_mock.call_args_list == []
    assert error_mock.call_args_list == []

    assert get_cache("activity:worker-0") == None
    assert get_cache("activity:worker-1") == None

    task = bc.database.get("task_manager.TaskManager", 1, dict=False)

    assert get_cache(f"activity:backup:{task.id}") == None

    assert get_table_mock.call_args_list == [
        call("dataset.activity"),
    ]

    both_schema_are_equal(
        update_table_mock.call_args_list,
        [
            call(
                TableMock(
                    [
                        bigquery.SchemaField("character", "STRING", "NULLABLE", None, None, (), None),
                        bigquery.SchemaField("kind", "STRING", "NULLABLE"),
                        bigquery.SchemaField("user_id", "INTEGER", "NULLABLE"),
                        bigquery.SchemaField("timestamp", "TIMESTAMP", "NULLABLE"),
                        bigquery.SchemaField(
                            "meta",
                            "RECORD",
                            "NULLABLE",
                            fields=(
                                bigquery.SchemaField(attr1, bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                                bigquery.SchemaField(attr2, bigquery.enums.SqlTypeNames.BOOL, "NULLABLE"),
                                bigquery.SchemaField(attr3, bigquery.enums.SqlTypeNames.FLOAT64, "NULLABLE"),
                                bigquery.SchemaField(attr4, bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                                bigquery.SchemaField("knife", "BOOL", "NULLABLE"),
                                bigquery.SchemaField("pistol", "FLOAT64", "NULLABLE"),
                            ),
                        ),
                        bigquery.SchemaField(
                            "related",
                            "RECORD",
                            "NULLABLE",
                            fields=(
                                bigquery.SchemaField("amount", "INT64", "NULLABLE"),
                                bigquery.SchemaField("id", "INTEGER", "NULLABLE"),
                                bigquery.SchemaField("name", "STRING", "NULLABLE"),
                                bigquery.SchemaField("type", "STRING", "NULLABLE"),
                                bigquery.SchemaField("slug", "STRING", "NULLABLE"),
                            ),
                        ),
                    ]
                ),
                ["schema"],
            )
        ],
    )
    assert insert_rows_mock.call_args_list == [call(get_table_mock.return_value, [data1, data2, data3])]
