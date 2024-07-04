from rest_framework.test import APITestCase
from datetime import datetime, timedelta, date
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    BreathecodeMixin,
)


class CareerTestCase(
    APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, HeadersMixin, DatetimeMixin, BreathecodeMixin
):
    """CertificateTestCase with auth methods"""

    def setUp(self):
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()

    def clear_keys(self, dicts, keys):
        _d = {}
        for k in keys:
            _d[k] = None

        return [{**item, **_d} for item in dicts]
