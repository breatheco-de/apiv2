"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin

class AdmissionsTestCase(APITestCase, GenerateModelsMixin, CacheMixin):
    """AdmissionsTestCase with auth methods"""
    pass
