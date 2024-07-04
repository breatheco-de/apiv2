from datetime import date, datetime, timedelta

from rest_framework.test import APITestCase

from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
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
