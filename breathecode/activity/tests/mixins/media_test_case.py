"""
Collections of mixins used to login in authorize microservice
"""
import os
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                                      HeadersMixin, DatetimeMixin, Sha256Mixin, BreathecodeMixin)
from breathecode.utils.sqlalchemy import BigQueryBase
from sqlalchemy import create_engine


class MediaTestCase(APITestCase, GenerateModelsMixin, CacheMixin, TokenMixin, GenerateQueriesMixin,
                    HeadersMixin, DatetimeMixin, Sha256Mixin, BreathecodeMixin):
    """FeedbackTestCase with auth methods"""

    def tearDown(self):
        BigQueryBase.metadata.drop_all(self.engine)
        self.clear_cache()

    def setUp(self):
        self.generate_queries()
        os.environ['MEDIA_GALLERY_BUCKET'] = 'bucket-name'
        self.set_test_instance(self)

        self.engine = create_engine('sqlite:///:memory:', echo=True)
        BigQueryBase.metadata.bind = self.engine
        BigQueryBase.metadata.create_all()  # Create tables
