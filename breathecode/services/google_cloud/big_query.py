import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from breathecode.services.google_cloud import credentials

engine = None

__all__ = ['BigQuery']


class BigQuery:

    @staticmethod
    def session():
        global engine

        credentials.resolve_credentials()

        if not engine:
            project = os.getenv('GOOGLE_PROJECT_ID', '')
            engine = create_engine(f'bigquery://{project}')

        session = sessionmaker(bind=engine)
        return session()

    @staticmethod
    def connection():
        global engine

        credentials.resolve_credentials()

        if not engine:
            project = os.getenv('GOOGLE_PROJECT_ID', '')
            engine = create_engine(f'bigquery://{project}')

        return engine.connect()
