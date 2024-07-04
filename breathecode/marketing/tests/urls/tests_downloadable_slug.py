"""
Test /downloadable
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.marketing.models import Downloadable
from ..mixins import MarketingTestCase


class DownloadableTestSuite(MarketingTestCase):
    """Test /downloadable"""

    def test_downloadable_slug_without_data(self):
        """Test /downloadable to check if it returns an empty list"""
        url = reverse_lazy("marketing:single_downloadable", kwargs={"slug": "test"})
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_downloadable_slug_with_data(self):
        """Test /downloadable to check if it returns an empty list"""
        model = self.generate_models(downloadable=True)
        url = reverse_lazy("marketing:single_downloadable", kwargs={"slug": f'{model["downloadable"].slug}'})
        response = self.client.get(url)
        json = response.json()
        expected = {
            "slug": f'{model["downloadable"].slug}',
            "name": f'{model["downloadable"].name}',
            "destination_url": f'{model["downloadable"].destination_url}',
            "preview_url": f'{model["downloadable"].preview_url}',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_downloadable_slug_with_data_with_redirect(self):
        """Test /downloadable to check if it returns an empty list"""
        model = self.generate_models(downloadable=True)
        url = reverse_lazy("marketing:single_downloadable", kwargs={"slug": f'{model["downloadable"].slug}'})
        response = self.client.get(url + "?raw=true")
        expected = model["downloadable"].destination_url

        self.assertEqual(response.url, expected)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.all_form_entry_dict(), [])
