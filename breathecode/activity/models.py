import json
import os

from google.cloud import bigquery, ndb
from sqlalchemy import JSON, TIMESTAMP, Column, Integer, String

from breathecode.utils.sqlalchemy import BigQueryBase


def is_test_env():
    return os.getenv("ENV") == "test" or True


class StudentActivity(ndb.Model):
    id = ndb.ModelKey()
    cohort = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()
    data = ndb.JsonProperty()
    day = ndb.IntegerProperty()
    email = ndb.StringProperty()
    slug = ndb.StringProperty()
    user_agent = ndb.StringProperty()
    user_id = ndb.IntegerProperty()
    academy_id = ndb.IntegerProperty()

    @classmethod
    def _get_kind(cls):
        return "student_activity"


class ActivityMeta(BigQueryBase):
    __tablename__ = "4geeks.activity_nested"

    email = Column(String(36), primary_key=True)
    related = Column(Integer, nullable=False)
    related_pk = Column(String(25), nullable=False)
    # related
    resource = Column(String(30), nullable=True)
    resource_id = Column(String(30), nullable=True)
    meta = Column(String, default="{}")
    meta = Column(JSON, default="{}")
    timestamp = Column(TIMESTAMP, nullable=False)


# this model is a example, it's useless because google can't support JSON on they own SQLAlchemy dialect
class Activity(BigQueryBase):
    __tablename__ = "4geeks.activity"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False)
    kind = Column(String(25), nullable=False)
    related = Column(String(30), nullable=True)
    related_id = Column(String(30), nullable=True)
    meta = Column(String, default="{}")
    timestamp = Column(TIMESTAMP, nullable=False)

    @property
    def json(self):
        return json.loads(self.meta)

    @json.setter
    def json(self, value):
        self.meta = json.dumps(value)


# it's required to transform all BigQuery models to SQLite, but it also is useless because it doesn't support JSON
# test_support(__name__)

ACTIVITY = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_id", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("kind", "STRING", mode="REQUIRED"),
    bigquery.SchemaField(
        "related",
        "RECORD",
        mode="NULLABLE",
        fields=[
            bigquery.SchemaField("type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("id", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("slug", "STRING", mode="NULLABLE"),
        ],
    ),
    bigquery.SchemaField(
        "meta",
        "RECORD",
        mode="REQUIRED",
        fields=[
            bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("username", "STRING", mode="NULLABLE"),
        ],
    ),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
]
