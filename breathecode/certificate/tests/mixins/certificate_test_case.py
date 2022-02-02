"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                                      DatetimeMixin, BreathecodeMixin)


class CertificateTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                          DatetimeMixin, BreathecodeMixin):
    """CertificateTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()
        self.set_test_instance(self)

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

    def clear_keys(self, dicts, keys):
        _d = {}
        for k in keys:
            _d[k] = None

        return [{**item, **_d} for item in dicts]

    def remove_is_clean(self, items):
        for item in items:
            if 'is_cleaned' in item:
                del item['is_cleaned']
        return items
