import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from breathecode.services.google_cloud import credentials
from breathecode.utils.sqlalchemy import BigQueryBase
from google.cloud import bigquery
from sqlalchemy.engine.mock import MockConnection
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials

client = None
engine = None

__all__ = ['BigQuery', 'BigQuerySet', 'Sum', 'Count', 'Avg']


def is_test_env():
    return os.getenv('ENV') == 'test'


class BigQueryMeta(type):

    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)

        try:
            cls._setup_engine()

        except Exception:
            pass


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
            engine = create_engine('sqlite:///:memory:', echo=False)

            client_options = ClientOptions(api_endpoint='http://0.0.0.0:9050')
            client = bigquery.Client(
                'test',
                client_options=client_options,
                credentials=AnonymousCredentials(),
            )

        if not engine:
            project = os.getenv('GOOGLE_PROJECT_ID', '')
            engine = create_engine(f'bigquery://{project}')

            credentials.resolve_credentials()
            client = bigquery.Client(location='us-central1')

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
    def client(cls) -> tuple[bigquery.Client, str]:
        """Get a BigQuery client instance and project id."""

        global client

        if not client:
            cls._setup_engine()

        credentials.resolve_credentials()
        return client, os.getenv('GOOGLE_PROJECT_ID', 'test'), os.getenv('BIGQUERY_DATASET', '')


class Sum():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class Count():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class Avg():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class BigQuerySet():

    def __init__(self, table):
        client, project_id, dataset = BigQuery.client()

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

    def set_query(self, *args, **kwargs):
        self.query.update(kwargs)

    def limit_by(self, name):
        self.limit = name
        return self

    def order_by(self, *name):
        self.order = name
        return self

    def group_by(self, *name):
        self.group = name
        return self

    def aggregate(self, *args):
        sql = self.sql(args)
        print(sql)
        params, kwparams = self.get_params()

        query_job = self.client.query(sql, *params, **kwparams)

        return query_job.result()

    def build(self):

        sql = self.sql()

        print(sql)
        params, kwparams = self.get_params()

        query_job = self.client.query(sql, *params, **kwparams)
        return query_job.result()

    def filter(self, *args, **kwargs):
        self.set_query(*args, **kwargs)
        return self

    def attribute_parser(self, key):
        operand = '='
        key = key.replace('__', '.')
        if key[-4:] == '.gte':
            key = key[:-4]
            operand = '>='
        elif key[-3:] == '.gt':
            key = key[:-3]
            operand = '>'
        elif key[-3:] == '.lt':
            key = key[:-3]
            operand = '<'
        if key[-4:] == '.lte':
            key = key[:-4]
            operand = '<='
        return key, operand, 'x__' + key.replace('.', '__')

    def get_type(self, elem):
        if isinstance(elem, int):
            return 'INT64'
        if isinstance(elem, float):
            return 'FLOAT64'
        if isinstance(elem, bool):
            return 'BOOL'
        if isinstance(elem, str):
            return 'STRING'
        if isinstance(elem, datetime):
            return 'DATETIME'

    def get_params(self):
        if not self.query:
            return [], {}
        params = []
        kwparams = {}
        query_params = []

        for key, val in self.query.items():
            key, operand, var_name = self.attribute_parser(key)
            query_params.append(bigquery.ScalarQueryParameter(var_name, self.get_type(val), val))

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        kwparams['job_config'] = job_config

        return params, kwparams

    def select(self, *names):
        self.fields = names
        return self

    def aggregation_parser(self, agg):
        operation = None
        attribute = None
        if isinstance(agg, Sum):
            operation = 'SUM'
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Count):
            operation = 'COUNT'
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Avg):
            operation = 'AVG'
            attribute = agg._constructor_args[0][0]

        return operation, attribute

    def sql(self, aggs=[]):
        query_fields = []
        if self.fields:
            query_fields += self.fields
        if aggs:
            for agg in aggs:
                operation, attribute = self.aggregation_parser(agg)
                query_fields.append(f'{operation}({attribute}) AS {operation.lower()}__{attribute}')

        if len(query_fields) > 0:
            query = f"""SELECT {", ".join(query_fields)} FROM `{self.project_id}.{self.dataset}.{self.table}` """
        else:
            query = f"""SELECT * FROM `{self.project_id}.{self.dataset}.{self.table}` """

        if self.query:
            query += 'WHERE '
            for key, val in self.query.items():
                key, operand, var_name = self.attribute_parser(key)
                query += f'{key} {operand} @{var_name} AND '
            query = query[:-5]

        if self.group:
            group_by = ', '.join(self.group)
            query += f' GROUP BY {group_by}'

        if self.order:
            order_by = ', '.join(self.order)
            query += f' ORDER BY {order_by} DESC'

        if self.limit:
            query += f' LIMIT {self.limit}'

        return query

    def json_query(self, query):
        if 'filter' in query:
            self.filter(**query['filter'])

        if 'fields' in query:
            self.select(*query['fields'])

        if 'by' in query:
            self.group_by(*query['by'])

        if 'order' in query:
            self.order_by(*query['order'])

        if 'limit' in query:
            self.limit_by(query['limit'])

        if 'grouping_function' in query:
            grouping_function = query['grouping_function']
            aggs = []
            if 'sum' in grouping_function:
                for value in grouping_function['sum']:
                    aggs.append(Sum(value))

            if 'count' in grouping_function:
                for value in grouping_function['count']:
                    aggs.append(Count(value))

            if 'avg' in grouping_function:
                for value in grouping_function['avg']:
                    aggs.append(Avg(value))

            result = self.aggregate(*aggs)
        else:
            result = self.build()

        return result
