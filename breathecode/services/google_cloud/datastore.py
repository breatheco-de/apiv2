import logging
from google.cloud import datastore
from .credentials import resolve_credentials

logger = logging.getLogger(__name__)


class Datastore:
    """Google Cloud Storage"""
    client = None

    def __init__(self):
        resolve_credentials()
        self.client = datastore.Client()

    def fetch(self, **kwargs):
        """Get Fetch object

        Args:
            **kwargs: Arguments to Google Cloud Datastore

        Returns:
            Fetch: Fetch object
        """
        return self.client.query(**kwargs).fetch()

    def update(self, key: str, data: dict):
        """Get Fetch object

        Args:
            **kwargs: Arguments to Google Cloud Datastore

        Returns:
            Fetch: Fetch object
        """
        entity = datastore.Entity(self.client.key(key))
        entity.update(data)
