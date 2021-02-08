"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, TokenMixin

class CertificateTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
        TokenMixin):
    """CertificateTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    # TODO: this function fix the difference between run tests in all modules
    # and certificate, should be removed in a future
    def clear_preview_url(self, dicts: list[dict]):
        """
        Clear preview url to evit one diff when run test in all tests and just
        certificate tests
        """
        return [{**item, 'preview_url': None} for item in dicts]
