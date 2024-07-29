"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase
from breathecode.tests.mixins import BreathecodeMixin, GenerateModelsMixin

__all__ = ["UtilsTestCase"]


class UtilsTestCase(APITestCase, BreathecodeMixin, GenerateModelsMixin):
    """UtilsTestCase with auth methods"""

    def setUp(self):
        self.set_test_instance(self)

    # def tearDown(self):
    #     self.clear_cache()
