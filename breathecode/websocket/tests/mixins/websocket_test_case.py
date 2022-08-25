"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, GenerateQueriesMixin,
                                      OldBreathecodeMixin, DatetimeMixin, BreathecodeMixin)


class WebsocketTestCase(APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin,
                        OldBreathecodeMixin, DatetimeMixin, BreathecodeMixin):
    """AdmissionsTestCase with auth methods"""

    def setUp(self):
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()
