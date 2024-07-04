"""
Collections of mixins used to login in authorize microservice
"""

import os

from rest_framework.test import APITestCase

from breathecode.tests.mixins import (
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    ICallMixin,
    BreathecodeMixin,
)


class CypressTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    ICallMixin,
    BreathecodeMixin,
):
    """AdmissionsTestCase with auth methods"""

    def setUp(self):
        os.environ["API_URL"] = "http://localhost:8000"
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()
