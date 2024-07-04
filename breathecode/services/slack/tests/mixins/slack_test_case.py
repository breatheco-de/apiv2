"""
Collections of mixins used to login in authorize microservice
"""

import re
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    GenerateQueriesMixin,
    DatetimeMixin,
    ICallMixin,
    BreathecodeMixin,
)
from rest_framework import status


class SlackTestCase(
    APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin, ICallMixin, BreathecodeMixin
):
    """SlackTestCase with auth methods"""

    def setUp(self):
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()
