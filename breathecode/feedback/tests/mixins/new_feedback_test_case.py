"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin

class FeedbackTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
        TokenMixin, GenerateQueriesMixin):
    """FeedbackTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.generate_queries()
        # print(self.__dict__)
