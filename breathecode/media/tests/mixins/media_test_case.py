"""
Collections of mixins used to login in authorize microservice
"""

import os

from rest_framework.test import APITestCase

from breathecode.media.models import Media
from breathecode.media.serializers import GetMediaSerializer
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

    def setUp(self):
        os.environ["MEDIA_GALLERY_BUCKET"] = "bucket-name"
        self.generate_queries()
        self.set_test_instance(self)

    def full_media_dict(self):
        all_media = Media.objects.all()
        all_media_dict = GetMediaSerializer(all_media, many=True)
        return all_media_dict.data
