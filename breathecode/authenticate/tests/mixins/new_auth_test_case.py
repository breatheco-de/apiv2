from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, HeadersMixin, TokenMixin
# from breathecode.admissions.tests.mixins.new_admissions_test_case import AdmissionsTestCase

class AuthTestCase(APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, HeadersMixin, TokenMixin):
    """AdmissionsTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()
        
    def tearDown(self):
        self.clear_cache()