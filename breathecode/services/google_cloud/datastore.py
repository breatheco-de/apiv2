import logging

import google.cloud.datastore as datastore

from .credentials import resolve_credentials

logger = logging.getLogger(__name__)

__all__ = ["Datastore"]


class Datastore:
    """Google Cloud Storage"""

    client = None

    def __init__(self):
        resolve_credentials()
        self.client = datastore.Client()

    def fetch(self, order_by=None, **kwargs):
        """Get Fetch object

        Args:
            **kwargs: Arguments to Google Cloud Datastore

        Returns:
            Fetch: Fetch object
        """
        kind = kwargs.pop("kind")
        query = self.client.query(kind=kind)

        limit = 100
        offset = 0

        if "offset" in kwargs:
            offset = kwargs["offset"]
            kwargs.pop("offset")

        if "limit" in kwargs:
            limit = kwargs["limit"]
            kwargs.pop("limit")

        for key in kwargs:
            query.add_filter(key, "=", kwargs[key])

        if order_by:
            query.order = order_by

        return list(query.fetch(limit=limit, offset=offset))

    def update(self, key: str, data: dict):
        """Get Fetch object

        Args:
            **kwargs: Arguments to Google Cloud Datastore

        Returns:
            Fetch: Fetch object
        """
        entity = datastore.Entity(self.client.key(key))
        entity.update(data)
        self.client.put(entity)

    def count(self, order_by=None, **kwargs):
        """
        Count method for total entities on a query

        """

        kind = kwargs.pop("kind")
        query = self.client.query(kind=kind)

        for key in kwargs:
            query.add_filter(key, "=", kwargs[key])

        query.keys_only()

        return len(list(query.fetch()))
