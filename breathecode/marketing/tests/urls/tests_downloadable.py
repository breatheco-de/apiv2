"""
Test /downloadable
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.marketing.models import Downloadable
from ..mixins import MarketingTestCase


class DownloadableTestSuite(MarketingTestCase):
    """Test /downloadable"""

    # TEST SHOULD COVER THE FOLLOWING:

    # - GET all downloadables: /marketing/downloadable
    # - GET single downloadable /marketing/downloadable/
    # - Redirect to single downloadable, same as above but add the?raw=true,
    # you should be redirected to the downloadable.destination_url
    # - Update the POST /marketing/lead test to make sure that the current_download
    # field is being property sent to activecampaign like all the other fields.

    def test_get_downloadables_without_model(self):
        """Test /downloadable to check if it returns an empty list"""
        url = reverse_lazy('marketing:downloadable')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    def test_get_downloadables_with_data_from_model(self):
        """Test /downloadable to check if it returns data after creating model"""
        url = reverse_lazy('marketing:downloadable')
        model = self.generate_models(downloadable=True)
        response = self.client.get(url)
        json = response.json()
        expected = []

        assertEqual(json, expected)
        assert False
