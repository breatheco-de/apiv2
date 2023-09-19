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
