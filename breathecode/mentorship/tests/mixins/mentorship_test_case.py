"""
Collections of mixins used to login in authorize microservice
"""
import os
from unittest.mock import call
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                                      HeadersMixin, DatetimeMixin, BreathecodeMixin)
from breathecode.authenticate.models import Token
from breathecode.notify.actions import get_template_content


class MentorshipTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                         HeadersMixin, DatetimeMixin, BreathecodeMixin):
    """FeedbackTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)

    def get_token_key(self, id=None):
        kwargs = {}
        if id:
            kwargs['id'] = id
        return Token.objects.filter(**kwargs).values_list('key', flat=True).first()
