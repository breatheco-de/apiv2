import os

from google.cloud import bigquery, ndb


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
