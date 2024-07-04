import datetime
import os
from typing import Any, Optional

from django.db.models import Avg, Count, Sum
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery
from google.cloud.bigquery.schema import SchemaField
from google.cloud.bigquery.table import RowIterator, Table
from sqlalchemy import create_engine
from sqlalchemy.engine.mock import MockConnection
from sqlalchemy.orm import sessionmaker

from breathecode.services.google_cloud import credentials
from breathecode.utils.sqlalchemy import BigQueryBase

client = None
engine = None

__all__ = ["BigQuery"]


def is_test_env():
    return os.getenv("ENV") == "test"


class BigQueryModel:

    def __init__(self, client: bigquery.Client, _project_id: str, _dataset: str, _table: str, **kwargs):

        self._project_id = _project_id
        self._dataset = _dataset
        self._table = _table
        self.client = client

        self.__dict__.update(kwargs)

    def __getattr__(self, __name: str) -> Any:
        self.__dict__.get(__name)

    def __setattr__(self, __name: str, __value: Any) -> None:
        self.__dict__[__name] = __value

    def __delattr__(self, __name: str) -> None:
        del self.__dict__[__name]

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return f'<BigQueryModel "{self._project_id}.{self._dataset}.{self._table}">'

    def save(self):
        table_ref = self.client.dataset(self._dataset, project=self._project_id).table(self._table)
        table = self.client.get_table(table_ref)

        row = [self.__dict__]

        errors = self.client.insert_rows(table, row)

        if errors:
            raise Exception(errors)


class BigQuerySet:
    query: dict[str, Any]
    agg: list[Any]
    fields: Optional[list[str]]
    order: Optional[list[str]]
    group: Optional[list[str]]
    limit: Optional[int]
    _limit: Optional[Table]

    def __init__(self, table: str, client: bigquery.Client, project_id: str, dataset: str) -> None:

        self.query = {}
        self.agg = []
        self.fields = None
        self.order = None
        self.group = None
        self.limit = None
        self.table = table
        self.client = client
        self.dataset = dataset
        self.project_id = project_id
        self._table_ref = None

    def _get_table(self) -> Table:
        if self._table_ref:
            return self._table_ref

        table_ref = f"{self.dataset}.{self.table}"

        # Fetch the schema of the table
        table = self.client.get_table(table_ref)
        # self.client.
        self._table_ref = table
        return self._table_ref

    def new(self, **kwargs) -> BigQueryModel:
        return BigQueryModel(client, self.project_id, self.dataset, self.table, **kwargs)

    def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        if len(rows) == 0:
            return None

        if isinstance(rows[0], BigQueryModel):
            rows = [x.__dict__ for x in rows]

        table = self._get_table()
        errors = self.client.insert_rows(table, rows)

        if errors:
            raise Exception(errors)

    def schema(self) -> list[SchemaField]:
        table = self._get_table()
        return table.schema

    def update_schema(self, schema: list[SchemaField]) -> None:
        table = self._get_table()
        table.schema = schema

        self.client.update_table(table, ["schema"])

    def set_query(self, *args: Any, **kwargs: Any) -> None:
        self.query.update(kwargs)

    def limit_by(self, name: int) -> "BigQuerySet":
        self.limit = name
        return self

    def order_by(self, *name: str) -> "BigQuerySet":
        self.order = name
        return self

    def group_by(self, *name: str) -> "BigQuerySet":
        self.group = name
        return self

    def aggregate(self, *args: Any) -> RowIterator:
        sql = self.sql(args)

        params, kwparams = self.get_params()

        query_job = self.client.query(sql, *params, **kwparams)

        return query_job.result()

    def build(self) -> RowIterator:
        sql = self.sql()

        params, kwparams = self.get_params()

        query_job = self.client.query(sql, *params, **kwparams)
        return query_job.result()

    def filter(self, *args: Any, **kwargs: Any) -> "BigQuerySet":
        self.set_query(*args, **kwargs)
        return self

    def attribute_parser(self, key: str) -> tuple[str, str, str]:
        operand = "="
        key = key.replace("__", ".")
        if key[-4:] == ".gte":
            key = key[:-4]
            operand = ">="
        elif key[-3:] == ".gt":
            key = key[:-3]
            operand = ">"
        elif key[-3:] == ".lt":
            key = key[:-3]
            operand = "<"
        if key[-4:] == ".lte":
            key = key[:-4]
            operand = "<="
        if key[-5:] == ".like":
            key = key[:-5]
            operand = "LIKE"
        return key, operand, "x__" + key.replace(".", "__")

    def get_type(self, elem: Any) -> None:
        if isinstance(elem, int):
            return "INT64"
        if isinstance(elem, float):
            return "FLOAT64"
        if isinstance(elem, bool):
            return "BOOL"
        if isinstance(elem, str):
            return "STRING"
        if isinstance(elem, datetime):
            return "DATETIME"

    def get_params(self) -> tuple[list[Any], dict[str, Any]]:
        if not self.query:
            return [], {}
        params = []
        kwparams = {}
        query_params = []

        for key, val in self.query.items():
            key, operand, var_name = self.attribute_parser(key)
            query_params.append(bigquery.ScalarQueryParameter(var_name, self.get_type(val), val))

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        kwparams["job_config"] = job_config

        return params, kwparams

    def select(self, *names: str) -> "BigQuerySet":
        self.fields = names
        return self

    def aggregation_parser(self, agg: Any) -> tuple[str, str]:
        operation = None
        attribute = None
        if isinstance(agg, Sum):
            operation = "SUM"
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Count):
            operation = "COUNT"
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Avg):
            operation = "AVG"
            attribute = agg._constructor_args[0][0]

        return operation, attribute

    def sql(self, aggs=None) -> str:
        if aggs is None:
            aggs = []

        query_fields = []
        if self.fields:
            query_fields += self.fields

        if aggs:
            for agg in aggs:
                operation, attribute = self.aggregation_parser(agg)
                query_fields.append(f'{operation}({attribute}) AS {operation.lower()}__{attribute.replace(".", "__")}')

        if len(query_fields) > 0:
            query = f"""SELECT {", ".join(query_fields)} FROM `{self.project_id}.{self.dataset}.{self.table}` """
        else:
            query = f"""SELECT * FROM `{self.project_id}.{self.dataset}.{self.table}` """

        if self.query:
            query += "WHERE "
            for key, _ in self.query.items():
                key, operand, var_name = self.attribute_parser(key)
                query += f"{key} {operand} @{var_name} AND "
            query = query[:-5]

        if self.group:
            group_by = ", ".join(self.group)
            query += f" GROUP BY {group_by}"

        if self.order:
            order_by = ", ".join(self.order)
            query += f" ORDER BY {order_by} DESC"

        if self.limit:
            query += f" LIMIT {self.limit}"

        return query

    def json_query(self, query: dict[str, Any]):
        if "filter" in query:
            self.filter(**query["filter"])

        if "fields" in query:
            self.select(*query["fields"])

        if "by" in query:
            self.group_by(*query["by"])

        if "order" in query:
            self.order_by(*query["order"])

        if "limit" in query:
            self.limit_by(query["limit"])

        if "grouping_function" in query:
            grouping_function = query["grouping_function"]
            aggs = []
            if "sum" in grouping_function:
                for value in grouping_function["sum"]:
                    aggs.append(Sum(value))

            if "count" in grouping_function:
                for value in grouping_function["count"]:
                    aggs.append(Count(value))

            if "avg" in grouping_function:
                for value in grouping_function["avg"]:
                    aggs.append(Avg(value))

            result = self.aggregate(*aggs)
        else:
            result = self.build()

        return result


class BigQueryMeta(type):

    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)

        try:
            cls._setup_engine()

        except Exception:
            pass


Schema = list[bigquery.SchemaField] | tuple[bigquery.SchemaField]
MappedSchema = dict[str, bigquery.SchemaField]


class BigQuery(metaclass=BigQueryMeta):

    @staticmethod
    def setup():
        """Create the database schema."""

        global engine

        BigQueryBase.metadata.bind = engine
        BigQueryBase.metadata.create_all()

    @staticmethod
    def teardown():
        """Destroy the database schema."""

        global engine

        BigQueryBase.metadata.drop_all(engine)

    @classmethod
    def _setup_engine(cls):
        global engine
        global client

        credentials.resolve_credentials()

        if not engine and is_test_env():
            engine = create_engine("sqlite:///:memory:", echo=False)

            client_options = ClientOptions(api_endpoint="http://0.0.0.0:9050")
            client = bigquery.Client(
                "test",
                client_options=client_options,
                credentials=AnonymousCredentials(),
            )

        if not engine:
            project = os.getenv("GOOGLE_PROJECT_ID", "")
            engine = create_engine(f"bigquery://{project}")

            credentials.resolve_credentials()
            client = bigquery.Client(location="us-central1")

    @classmethod
    def session(cls) -> sessionmaker:
        """Get a BigQuery session instance."""

        global engine

        if not engine:
            cls._setup_engine()

        credentials.resolve_credentials()
        session = sessionmaker(bind=engine)
        return session()

    @classmethod
    def connection(cls) -> MockConnection:
        """Get a BigQuery connection instance."""

        global engine

        if not engine:
            cls._setup_engine()

        credentials.resolve_credentials()
        return engine.connect()

    @classmethod
    def client(cls) -> tuple[bigquery.Client, str, str]:
        """Get a BigQuery client instance and project id."""

        global client

        if not client:
            cls._setup_engine()

        credentials.resolve_credentials()
        return client, os.getenv("GOOGLE_PROJECT_ID", "test"), os.getenv("BIGQUERY_DATASET", "")

    @classmethod
    def table(cls, table: str) -> BigQuerySet:
        """Get a BigQuery client instance and project id."""

        client, project_id, dataset = cls.client()

        return BigQuerySet(table, client, project_id, dataset)

    @classmethod
    def _map_schema(cls, schema: Schema) -> MappedSchema:
        res = {}

        for field in schema:
            res[field.name] = field

        return res

    @classmethod
    def join_schemas(
        cls,
        *schemas: Schema,
    ) -> BigQuerySet:
        """Join n schemas into one."""

        res: MappedSchema = {}

        for schema in schemas:
            new = cls._map_schema(schema)
            new_keys = set(new.keys())
            res_keys = set(res.keys())

            common = new_keys.intersection(res_keys)
            added = new_keys - res_keys

            for key in added:
                new_field = new[key]
                res[key] = new_field

            for key in common:
                new_field = new[key]
                if new_field.field_type == bigquery.enums.SqlTypeNames.STRUCT:
                    new_field._fields = cls.join_schemas(res[key].fields, new_field.fields)
                    res[key] = new_field

                elif new_field != res[key]:
                    res[key] = new_field

        return res.values()

    @classmethod
    def schema_difference(cls, old_schema: Schema, new_schema: Schema) -> BigQuerySet:
        """Get the difference between two schemas."""

        res = []
        old = cls._map_schema(old_schema)
        new = cls._map_schema(new_schema)

        new_keys = set(new.keys())
        old_keys = set(old.keys())

        added = new_keys - old_keys
        # removed = old_keys - new_keys
        common = new_keys.intersection(old_keys)

        for key in added:
            new_field = new[key]
            res.append(new_field)

        for key in common:
            new_field = new[key]
            if new_field.field_type == bigquery.enums.SqlTypeNames.STRUCT:
                new_field._fields = cls.schema_difference(old[key].fields, new_field.fields)
                if len(new_field._fields) > 0:
                    res.append(new_field)

            elif new_field != old[key]:
                res.append(new_field)

        return res

    @classmethod
    def merge_schema(cls, diff: Schema, schema: Schema) -> BigQuerySet:
        """Add the difference of the new schema to the original"""

        res = []
        diff_map = cls._map_schema(diff)
        schema_map = cls._map_schema(schema)

        diff_keys = set(diff_map.keys())
        schema_keys = set(schema_map.keys())

        original = schema_keys - diff_keys

        for key in original:
            field = schema_map[key]
            res.append(field)

        for key in diff_map:
            new_field = diff_map[key]
            if new_field.field_type == bigquery.enums.SqlTypeNames.STRUCT:
                old_field = schema_map[key]

                new_field._fields = cls.merge_schema(new_field.fields, old_field.fields)

                if len(new_field._fields) > 0:
                    res.append(new_field)

            elif key not in schema_map:
                res.append(new_field)

        return res
