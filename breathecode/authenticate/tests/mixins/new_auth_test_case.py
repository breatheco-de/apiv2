import os
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    TokenMixin,
    BreathecodeMixin,
)


class AuthTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    TokenMixin,
    BreathecodeMixin,
):
    """AdmissionsTestCase with auth methods"""

    def setUp(self):
        os.environ["API_URL"] = "http://localhost:8000"
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()
