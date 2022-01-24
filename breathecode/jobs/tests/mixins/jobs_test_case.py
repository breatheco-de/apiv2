from rest_framework.test import APITestCase
from datetime import datetime, timedelta, date
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin, DatetimeMixin


class JobsTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                   DatetimeMixin):
    """CertificateTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()

    def tearDown(self):
        self.clear_cache()

    def clear_keys(self, dicts, keys):
        _d = {}
        for k in keys:
            _d[k] = None

        return [{**item, **_d} for item in dicts]
