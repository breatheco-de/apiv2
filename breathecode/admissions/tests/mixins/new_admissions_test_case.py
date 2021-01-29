"""
Collections of mixins used to login in authorize microservice
"""
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin

class AdmissionsTestCase(APITestCase, GenerateModelsMixin):
    """AdmissionsTestCase with auth methods"""
    pass
