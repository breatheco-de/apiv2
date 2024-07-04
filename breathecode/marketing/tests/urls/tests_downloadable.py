"""
Test /downloadable
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.marketing.models import Downloadable
from ..mixins import MarketingTestCase


class DownloadableTestSuite(MarketingTestCase):
    """Test /downloadable"""

    def test_downloadable_without_model(self):
        """Test /downloadable to check if it returns an empty list"""
        url = reverse_lazy("marketing:downloadable")
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_downloadable_with_data(self):
        """Test /downloadable to check if it returns data after creating model"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=True)
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "destination_url": model["downloadable"].destination_url,
                "name": model["downloadable"].name,
                "preview_url": model["downloadable"].preview_url,
                "slug": model["downloadable"].slug,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_multiple_data(self):
        """Test /downloadable to check if it returns data after creating model"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "destination_url": model["downloadable"][0].destination_url,
                "name": model["downloadable"][0].name,
                "preview_url": model["downloadable"][0].preview_url,
                "slug": model["downloadable"][0].slug,
            },
            {
                "destination_url": model["downloadable"][1].destination_url,
                "name": model["downloadable"][1].name,
                "preview_url": model["downloadable"][1].preview_url,
                "slug": model["downloadable"][1].slug,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_incorrect_academy(self):
        """Test /downloadable to check if it returns data from one downloadable depending on academy"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(url + f"?academy=test")
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_one_academy(self):
        """Test /downloadable to check if it returns data from one downloadable depending on academy"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(url + f'?academy={model["downloadable"][0].academy.slug}')
        json = response.json()
        expected = [
            {
                "destination_url": model["downloadable"][0].destination_url,
                "name": model["downloadable"][0].name,
                "preview_url": model["downloadable"][0].preview_url,
                "slug": model["downloadable"][0].slug,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_multiple_academy(self):
        """Test /downloadable to check if it returns data from one downloadable depending on academy"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(
            url + f'?academy={model["downloadable"][0].academy.slug},{model["downloadable"][1].academy.slug}'
        )
        json = response.json()
        expected = [
            {
                "destination_url": model["downloadable"][0].destination_url,
                "name": model["downloadable"][0].name,
                "preview_url": model["downloadable"][0].preview_url,
                "slug": model["downloadable"][0].slug,
            },
            {
                "destination_url": model["downloadable"][1].destination_url,
                "name": model["downloadable"][1].name,
                "preview_url": model["downloadable"][1].preview_url,
                "slug": model["downloadable"][1].slug,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_active_true(self):
        """Test /downloadable to check if it returns data if academy is active"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(url + f"?active=true")
        json = response.json()
        expected = [
            {
                "destination_url": model["downloadable"][0].destination_url,
                "name": model["downloadable"][0].name,
                "preview_url": model["downloadable"][0].preview_url,
                "slug": model["downloadable"][0].slug,
            },
            {
                "destination_url": model["downloadable"][1].destination_url,
                "name": model["downloadable"][1].name,
                "preview_url": model["downloadable"][1].preview_url,
                "slug": model["downloadable"][1].slug,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_downloadable_with_active_false(self):
        """Test /downloadable to check if it returns data if academy is active"""
        url = reverse_lazy("marketing:downloadable")
        model = self.generate_models(downloadable=2)
        response = self.client.get(url + f"?active=false")
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
