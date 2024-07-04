"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase

from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    TokenMixin,
)


class PaymentsTestCase(
    APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin, DatetimeMixin, BreathecodeMixin
):
    """MarketingTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.maxDiff = None
        self.set_test_instance(self)
        self.bc.database.reset_queries()
