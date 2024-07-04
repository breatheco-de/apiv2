from breathecode.services.google_cloud.credentials import resolve_credentials

__all__ = ["NDB"]


class NDB:

    def __init__(self, model):
        from google.cloud import ndb

        resolve_credentials()
        self.client = ndb.Client()
        self.Model = model

    def fetch(self, query, **kwargs):
        from google.cloud import ndb

        client = ndb.Client()

        with client.context():
            query = self.Model.query().filter(*query)

            elements = query.fetch(**kwargs)
            return [c.to_dict() for c in elements]

    def count(self, query):
        from google.cloud import ndb

        client = ndb.Client()

        with client.context():
            query = self.Model.query().filter(*query)
            return query.count()
