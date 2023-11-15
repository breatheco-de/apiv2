import os
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

__all__ = ['BigQuery']


def is_test_env():
    return os.getenv('ENV') == 'test'


class BigQueryMeta(type):

    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)

        try:
            cls._setup_engine()

        except Exception:
            pass


class BigQuerySet():

    def __init__(self):
        self.query = {}
        self.agg = []
        self.group = None

    def set_query(self, *args, **kwargs):
        self.query.update(kwargs)

    def order_by(self, *name):
        self.group = name

    def aggregate(self, *args):
        self.agg += args

    def build(self, table, *, fields=[], **kwargs):
        if fields:
            query = f'SELECT {", ".join(fields)} FROM {table}'

        else:
            query = f'SELECT * FROM {table}'

        exact = []
        gt = []
        gte = []
        lt = []
        lte = []
        by = []

        for key in kwargs:
            if key.endswith('__gt'):
                gt.append({'k': key.replace('__gt', ''), 'v': kwargs[key]})

            elif key.endswith('__gte'):
                gte.append({'k': key.replace('__gte', ''), 'v': kwargs[key]})

            elif key.endswith('__lt'):
                lt.append({'k': key.replace('__lt', ''), 'v': kwargs[key]})

            elif key.endswith('__lte'):
                lte.append({'k': key.replace('__lte', ''), 'v': kwargs[key]})

            elif key.endswith('__by'):
                lte.append({'k': key.replace('__by', ''), 'v': kwargs[key]})

            else:
                exact.append({'k': key, 'v': kwargs[key]})

        if gt or gte or lt or lte or exact:
            query += ' WHERE '

            for o in gt:
                query += f'{o["k"]} > {o["v"]} AND '

            for o in gte:
                query += f'{o["k"]} >= {o["v"]} AND '

            for o in lt:
                query += f'{o["k"]} < {o["v"]} AND '

            for o in lte:
                query += f'{o["k"]} <= {o["v"]} AND '

            for o in exact:
                query += f'{o["k"]} = {o["v"]} AND '

            if query.endswith(' AND '):
                query = query[:-5]

        if self.group:
            query += ' GROUP BY ' + ', '.join(self.group)

        if self.agg:
            return
        """
        {"grouping_functions": [{
            "AVG": "salary", -> salary__avg
        }{
            "AVG": "edad", -> edad__avg
        },]}

        """

        return query


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

    @classmethod
    def select(cls, table, *, fields=[], **kwargs):
        if fields:
            query = f'SELECT {", ".join(fields)} FROM {table}'

        else:
            query = f'SELECT * FROM {table}'

        exact = []
        gt = []
        gte = []
        lt = []
        lte = []
        by = []

        for key in kwargs:
            if key.endswith('__gt'):
                gt.append({'k': key.replace('__gt', ''), 'v': kwargs[key]})

            elif key.endswith('__gte'):
                gte.append({'k': key.replace('__gte', ''), 'v': kwargs[key]})

            elif key.endswith('__lt'):
                lt.append({'k': key.replace('__lt', ''), 'v': kwargs[key]})

            elif key.endswith('__lte'):
                lte.append({'k': key.replace('__lte', ''), 'v': kwargs[key]})

            elif key.endswith('__by'):
                lte.append({'k': key.replace('__by', ''), 'v': kwargs[key]})

            else:
                exact.append({'k': key, 'v': kwargs[key]})

        if gt or gte or lt or lte or exact:
            query += ' WHERE '

            for o in gt:
                query += f'{o["k"]} > {o["v"]} AND '

            for o in gte:
                query += f'{o["k"]} >= {o["v"]} AND '

            for o in lt:
                query += f'{o["k"]} < {o["v"]} AND '

            for o in lte:
                query += f'{o["k"]} <= {o["v"]} AND '

            for o in exact:
                query += f'{o["k"]} = {o["v"]} AND '

            if query.endswith(' AND '):
                query = query[:-5]

        if by:
            query += ' GROUP BY ' + ', '.join(by)
        """
        {"grouping_functions": [{
            "AVG": "salary", -> salary__avg
        }{
            "AVG": "edad", -> edad__avg
        },]}

        """

        return query
