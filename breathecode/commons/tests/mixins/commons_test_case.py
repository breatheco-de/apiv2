"""
Collections of mixins used to login in authorize microservice
"""
import os
import re
from breathecode.authenticate.models import Token
from unittest.mock import call
from breathecode.notify.actions import get_template_content
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                                      DatetimeMixin, BreathecodeMixin)
from breathecode.feedback.actions import strings


class CommonsTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                      DatetimeMixin, BreathecodeMixin):
    """MarketingTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)
