"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, TokenMixin

class CertificateTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin):
    """CertificateTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()
