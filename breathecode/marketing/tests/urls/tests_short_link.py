from unittest.mock import Mock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MarketingTestCase


class ShortLinkTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Put
    """
    def test_short_link__no_auth(self):

        url = reverse_lazy('marketing:academy_short')
        response = self.client.put(url)

        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(response.json(), expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_short_slug(self):
        self.bc.help()
        url = reverse_lazy('marketing:academy_short')
        response = self.client.put(url)

        expected = {}

        self.assertEqual(response.json(), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
