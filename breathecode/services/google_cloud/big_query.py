import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from breathecode.services.google_cloud import credentials
from breathecode.utils.sqlalchemy import BigQueryBase

engine = None

__all__ = ['BigQuery']


def is_test_env():
    return os.getenv('ENV') == 'test' or True


class BigQueryMeta(type):

    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)
        cls.setup_engine()


class BigQuery(metaclass=BigQueryMeta):

    @staticmethod
    def setup():
        BigQueryBase.metadata.bind = engine
        BigQueryBase.metadata.create_all()

    @staticmethod
    def teardown():
        BigQueryBase.metadata.drop_all(engine)

    @classmethod
    def setup_engine(cls):
        global engine

        if not engine and is_test_env():
            engine = create_engine('sqlite:///:memory:', echo=False)

        if not engine:
            project = os.getenv('GOOGLE_PROJECT_ID', '')
            engine = create_engine(f'bigquery://{project}')

    @staticmethod
    def session():
        global engine

        credentials.resolve_credentials()
        session = sessionmaker(bind=engine)
        return session()

    @staticmethod
    def connection():
        global engine

        credentials.resolve_credentials()
        return engine.connect()
