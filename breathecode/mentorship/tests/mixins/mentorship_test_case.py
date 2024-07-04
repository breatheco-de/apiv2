"""
Collections of mixins used to login in authorize microservice
"""

from rest_framework.test import APITestCase

from breathecode.authenticate.models import Token
from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    TokenMixin,
)


class MentorshipTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    BreathecodeMixin,
):
    """FeedbackTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.set_test_instance(self)

    def get_token_key(self, id=None):
        kwargs = {}
        if id:
            kwargs["id"] = id
        return Token.objects.filter(**kwargs).values_list("key", flat=True).first()
