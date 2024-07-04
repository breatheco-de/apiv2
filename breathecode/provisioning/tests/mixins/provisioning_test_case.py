"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, BreathecodeMixin


class ProvisioningTestCase(APITestCase, GenerateModelsMixin, CacheMixin, BreathecodeMixin):
    """FeedbackTestCase with auth methods"""

    maxDiff = None

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)
