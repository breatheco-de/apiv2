"""
Collections of mixins used to login in authorize microservice
"""
import os
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    Sha256Mixin
)
from breathecode.media.models import Media
from breathecode.media.serializers import GetMediaSerializer
class MediaTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
        TokenMixin, GenerateQueriesMixin, HeadersMixin, DatetimeMixin,
        Sha256Mixin):
    """FeedbackTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.generate_queries()
        os.environ['MEDIA_GALLERY_BUCKET'] = 'bucket-name'

    def full_media_dict(self):
        all_media = Media.objects.all()
        all_media_dict = GetMediaSerializer(all_media, many=True)
        return  all_media_dict.data
