"""
Collections of mixins used to login in authorize microservice
"""

import os

from rest_framework.test import APITestCase

from breathecode.services.google_cloud import BigQuery
from breathecode.tests.mixins import (
    BreathecodeMixin,
    CacheMixin,
    DatetimeMixin,
    GenerateModelsMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    Sha256Mixin,
    TokenMixin,
)


class MediaTestCase(
    APITestCase,
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    Sha256Mixin,
    BreathecodeMixin,
):
    """FeedbackTestCase with auth methods"""

    def tearDown(self):
        self.clear_cache()
        BigQuery.teardown()

    def setUp(self):
        self.generate_queries()
        os.environ["MEDIA_GALLERY_BUCKET"] = "bucket-name"
        self.set_test_instance(self)

        BigQuery.setup()
