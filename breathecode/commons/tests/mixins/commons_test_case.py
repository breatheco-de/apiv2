"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    DatetimeMixin,
    BreathecodeMixin,
)


class CommonsTestCase(
    APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin, DatetimeMixin, BreathecodeMixin
):
    """MarketingTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)
