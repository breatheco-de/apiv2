"""
Test /answer/:id
"""
from breathecode.marketing.tasks import create_form_entry
import re, string, os
from datetime import datetime
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from random import choice, choices, randint
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_mailgun_requests_post_mock,
    OLD_BREATHECODE_PATH,
    OLD_BREATHECODE_INSTANCES,
    apply_old_breathecode_requests_request_mock,
    REQUESTS_PATH,
    apply_requests_get_mock,
)
from ..mixins import MarketingTestCase
from faker import Faker

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)

fake = Faker()
fake_url = fake.url()


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


def generate_form_entry_kwargs():
    """That random values is too long that i prefer have it in one function"""
    return {
        'fb_leadgen_id': randint(0, 9999),
        'fb_page_id': randint(0, 9999),
        'fb_form_id': randint(0, 9999),
        'fb_adgroup_id': randint(0, 9999),
        'fb_ad_id': randint(0, 9999),
        'gclid': random_string(),
        'first_name': choice(['Rene', 'Albert', 'Immanuel']),
        'last_name': choice(['Descartes', 'Camus', 'Kant']),
        'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
        'phone': '123456789',
        'course': random_string(),
        'client_comments': random_string(),
        'location': random_string(),
        'language': 'en',
        'utm_url': random_string(),
        'utm_medium': random_string(),
        'utm_campaign': random_string(),
        'utm_source': random_string(),
        'referral_key': random_string(),
        'gclid': random_string(),
        'tags': random_string(),
        'automations': random_string(),
        'street_address': random_string(),
        'country': random_string(),
        'city': random_string(),
        'latitude': 15,
        'longitude': 15,
        'state': random_string(),
        'zip_code': randint(0, 9999),
        'browser_lang': random_string(),
        'storage_status': choice(['PENDING', 'PERSISTED']),
        'lead_type': choice(['STRONG', 'SOFT', 'DISCOVERY']),
        'deal_status': choice(['WON', 'LOST']),
        'sentiment': choice(['GOOD', 'BAD']),
        'current_download': fake_url,
    }


class CreateFormEntryTestSuite(MarketingTestCase):
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_create_form_entry_with_dict_empty(self):
        """Test create_form_entry task without data"""
        try:
            create_form_entry({}, 1)
            assert False
        except Exception as e:
            print(e)
            message = str(e)
            self.assertEqual(message, 'You need to specify the form entry data')

        self.assertEqual(self.count_form_entry(), 0)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_persist_single_lead_dict_empty(self):
    #     """Test /answer/:id without auth"""
    #     try:
    #         persist_single_lead({})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'Missing location information')

    #     self.assertEqual(self.count_form_entry(), 0)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_persist_single_lead_with_bad_location(self):
    #     """Test /answer/:id without auth"""
    #     try:
    #         persist_single_lead({'location': 'they-killed-kenny'})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'No academy found with slug they-killed-kenny')

    #     self.assertEqual(self.count_form_entry(), 0)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_persist_single_lead_with_location(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True, active_campaign_academy=True)
    #     try:
    #         persist_single_lead({'location': model['academy'].slug})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'You need to specify tags for this entry')

    #     self.assertEqual(self.count_form_entry(), 0)
