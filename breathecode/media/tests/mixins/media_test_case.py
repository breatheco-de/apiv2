"""
Collections of mixins used to login in authorize microservice
"""
import os
from rest_framework.test import APITestCase
from ...models import Media, MediaResolution, Category
from breathecode.tests.mixins import (
    GenerateModelsMixin,
    CacheMixin,
    TokenMixin,
    GenerateQueriesMixin,
    HeadersMixin,
    DatetimeMixin,
    Sha256Mixin
)

class MediaTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
        TokenMixin, GenerateQueriesMixin, HeadersMixin, DatetimeMixin,
        Sha256Mixin):
    """FeedbackTestCase with auth methods"""
    def tearDown(self):
        self.clear_cache()

    def setUp(self):
        self.generate_queries()
        os.environ['MEDIA_GALLERY_BUCKET'] = 'bucket-name'

    def count_media_resolution(self):
        return MediaResolution.objects.count()

    def get_media_resolution_dict(self, id):
        data = MediaResolution.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None
