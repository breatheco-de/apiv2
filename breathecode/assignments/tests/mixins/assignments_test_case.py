"""
Collections of mixins used to login in authorize microservice
"""
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin, ICallMixin
from rest_framework import status


class AssignmentsTestCase(APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin,
                          ICallMixin):
    """AssignmentsTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()
