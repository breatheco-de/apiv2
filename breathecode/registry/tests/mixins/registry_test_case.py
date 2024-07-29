"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, BreathecodeMixin


class RegistryTestCase(APITestCase, GenerateModelsMixin, CacheMixin, BreathecodeMixin):
    """FeedbackTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)
