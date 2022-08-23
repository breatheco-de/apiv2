"""
Test /academy/lead
"""
from django.utils import timezone
from datetime import timedelta
import re, string
from random import choice, choices, randint
from mixer.main import Mixer
from unittest.mock import PropertyMock, patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from faker import Faker
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MarketingTestCase

fake = Faker()


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


class Fake_Recaptcha:

    class Risk_Analysis:

        def __init__(self, *args, **kwargs):
            self.score = 0.9

    def __init__(self, *args, **kwargs):
        self.risk_analysis = self.Risk_Analysis()


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
        'phone': choice(['123', '456', '789']),
        'course': random_string(),
        'client_comments': random_string(),
        'location': random_string(),
        'language': random_string(),
        'utm_url': fake.url(),
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
        'latitude': randint(0, 9999),
        'longitude': randint(0, 9999),
        'state': random_string(),
        'token': random_string(),
        'action': 'submit',
        'zip_code': randint(0, 9999),
        'browser_lang': random_string(),
        'storage_status': choice(['PENDING', 'PERSISTED']),
        'lead_type': choice(['STRONG', 'SOFT', 'DISCOVERY']),
        'deal_status': choice(['WON', 'LOST']),
        'sentiment': choice(['GOOD', 'BAD']),
        'current_download': random_string(),
    }


class LeadTestSuite(MarketingTestCase):
    """Test /academy/lead"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__without_data(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:lead')

        response = self.client.post(url)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': None,
                'fb_page_id': None,
                'fb_form_id': None,
                'fb_adgroup_id': None,
                'fb_ad_id': None,
                'first_name': '',
                'last_name': '',
                'email': None,
                'phone': None,
                'course': None,
                'client_comments': None,
                'current_download': None,
                'location': None,
                'language': 'en',
                'utm_url': None,
                'utm_medium': None,
                'utm_campaign': None,
                'utm_content': None,
                'utm_source': None,
                'referral_key': None,
                'gclid': None,
                'tags': '',
                'automations': '',
                'street_address': None,
                'country': None,
                'city': None,
                'latitude': None,
                'longitude': None,
                'state': None,
                'zip_code': None,
                'browser_lang': None,
                'storage_status': 'PENDING',
                'lead_type': None,
                'deal_status': None,
                'sentiment': None,
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': None,
                'user': None,
                'lead_generation_app': None,
                'tag_objects': [],
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': None,
            'fb_page_id': None,
            'fb_form_id': None,
            'fb_adgroup_id': None,
            'fb_ad_id': None,
            'first_name': '',
            'last_name': '',
            'email': None,
            'phone': None,
            'course': None,
            'client_comments': None,
            'current_download': None,
            'location': None,
            'language': 'en',
            'utm_url': None,
            'utm_medium': None,
            'utm_content': None,
            'utm_campaign': None,
            'utm_source': None,
            'referral_key': None,
            'gclid': None,
            'tags': '',
            'automations': '',
            'street_address': None,
            'country': None,
            'city': None,
            'latitude': None,
            'longitude': None,
            'state': None,
            'zip_code': None,
            'browser_lang': None,
            'storage_status': 'PENDING',
            'lead_type': None,
            'deal_status': None,
            'sentiment': None,
            'academy_id': None,
            'user_id': None,
            'ac_contact_id': None,
            'ac_deal_id': None,
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': None
        }])

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__with__bad_data(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(
            json, {
                'phone':
                ["Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."],
                'language': ['Ensure this field has no more than 2 characters.']
            })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__with__data(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        data['phone'] = '123456789'
        data['language'] = 'en'

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': data['fb_leadgen_id'],
                'fb_page_id': data['fb_page_id'],
                'fb_form_id': data['fb_form_id'],
                'fb_adgroup_id': data['fb_adgroup_id'],
                'fb_ad_id': data['fb_ad_id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone'],
                'course': data['course'],
                'client_comments': data['client_comments'],
                'current_download': data['current_download'],
                'location': data['location'],
                'language': data['language'],
                'utm_url': data['utm_url'],
                'utm_medium': data['utm_medium'],
                'utm_campaign': data['utm_campaign'],
                'utm_source': data['utm_source'],
                'utm_content': None,
                'referral_key': data['referral_key'],
                'gclid': data['gclid'],
                'tags': data['tags'],
                'automations': data['automations'],
                'street_address': data['street_address'],
                'country': data['country'],
                'city': data['city'],
                'latitude': json['latitude'],
                'longitude': json['longitude'],
                'state': data['state'],
                'zip_code': data['zip_code'],
                'browser_lang': data['browser_lang'],
                'storage_status': data['storage_status'],
                'lead_type': data['lead_type'],
                'deal_status': data['deal_status'],
                'sentiment': data['sentiment'],
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': None,
                'user': None,
                'lead_generation_app': None,
                'tag_objects': [],
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': json['fb_leadgen_id'],
            'fb_page_id': json['fb_page_id'],
            'fb_form_id': json['fb_form_id'],
            'fb_adgroup_id': json['fb_adgroup_id'],
            'fb_ad_id': json['fb_ad_id'],
            'first_name': json['first_name'],
            'last_name': json['last_name'],
            'email': json['email'],
            'phone': json['phone'],
            'course': json['course'],
            'client_comments': json['client_comments'],
            'current_download': json['current_download'],
            'location': json['location'],
            'language': json['language'],
            'utm_url': json['utm_url'],
            'utm_medium': json['utm_medium'],
            'utm_campaign': json['utm_campaign'],
            'utm_content': None,
            'utm_source': json['utm_source'],
            'referral_key': json['referral_key'],
            'gclid': json['gclid'],
            'tags': json['tags'],
            'automations': json['automations'],
            'street_address': json['street_address'],
            'country': json['country'],
            'city': json['city'],
            'latitude': float(json['latitude']),
            'longitude': float(json['longitude']),
            'state': json['state'],
            'zip_code': json['zip_code'],
            'browser_lang': json['browser_lang'],
            'storage_status': json['storage_status'],
            'lead_type': json['lead_type'],
            'deal_status': json['deal_status'],
            'sentiment': json['sentiment'],
            'academy_id': None,
            'user_id': None,
            'ac_contact_id': json['ac_contact_id'],
            'ac_deal_id': json['ac_deal_id'],
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': json['won_at']
        }])

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__with__data_active_campaign_slug(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(academy=True, academy_kwargs={'active_campaign_slug': 'midgard'})
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        data['phone'] = '123456789'
        data['language'] = 'en'
        data['location'] = 'midgard'

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': data['fb_leadgen_id'],
                'fb_page_id': data['fb_page_id'],
                'fb_form_id': data['fb_form_id'],
                'fb_adgroup_id': data['fb_adgroup_id'],
                'fb_ad_id': data['fb_ad_id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone'],
                'course': data['course'],
                'client_comments': data['client_comments'],
                'current_download': data['current_download'],
                'location': data['location'],
                'language': data['language'],
                'utm_url': data['utm_url'],
                'utm_medium': data['utm_medium'],
                'utm_campaign': data['utm_campaign'],
                'utm_content': None,
                'utm_source': data['utm_source'],
                'referral_key': data['referral_key'],
                'gclid': data['gclid'],
                'tags': data['tags'],
                'automations': data['automations'],
                'street_address': data['street_address'],
                'country': data['country'],
                'city': data['city'],
                'latitude': json['latitude'],
                'longitude': json['longitude'],
                'state': data['state'],
                'zip_code': data['zip_code'],
                'browser_lang': data['browser_lang'],
                'storage_status': data['storage_status'],
                'lead_type': data['lead_type'],
                'deal_status': data['deal_status'],
                'sentiment': data['sentiment'],
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': 1,
                'user': None,
                'tag_objects': [],
                'lead_generation_app': None,
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': json['fb_leadgen_id'],
            'fb_page_id': json['fb_page_id'],
            'fb_form_id': json['fb_form_id'],
            'fb_adgroup_id': json['fb_adgroup_id'],
            'fb_ad_id': json['fb_ad_id'],
            'first_name': json['first_name'],
            'last_name': json['last_name'],
            'email': json['email'],
            'phone': json['phone'],
            'course': json['course'],
            'client_comments': json['client_comments'],
            'current_download': json['current_download'],
            'location': json['location'],
            'language': json['language'],
            'utm_url': json['utm_url'],
            'utm_medium': json['utm_medium'],
            'utm_campaign': json['utm_campaign'],
            'utm_source': json['utm_source'],
            'utm_content': json['utm_content'],
            'referral_key': json['referral_key'],
            'gclid': json['gclid'],
            'tags': json['tags'],
            'automations': json['automations'],
            'street_address': json['street_address'],
            'country': json['country'],
            'city': json['city'],
            'latitude': float(json['latitude']),
            'longitude': float(json['longitude']),
            'state': json['state'],
            'zip_code': json['zip_code'],
            'browser_lang': json['browser_lang'],
            'storage_status': json['storage_status'],
            'lead_type': json['lead_type'],
            'deal_status': json['deal_status'],
            'sentiment': json['sentiment'],
            'academy_id': 1,
            'user_id': None,
            'ac_contact_id': json['ac_contact_id'],
            'ac_deal_id': json['ac_deal_id'],
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': json['won_at']
        }])

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__with__data_alias_active_campaign_slug(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(academy=True,
                             academy_alias=True,
                             academy_alias_kwargs={'active_campaign_slug': 'midgard'})
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        data['phone'] = '123456789'
        data['language'] = 'en'
        data['location'] = 'midgard'

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': data['fb_leadgen_id'],
                'fb_page_id': data['fb_page_id'],
                'fb_form_id': data['fb_form_id'],
                'fb_adgroup_id': data['fb_adgroup_id'],
                'fb_ad_id': data['fb_ad_id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone'],
                'course': data['course'],
                'client_comments': data['client_comments'],
                'current_download': data['current_download'],
                'location': data['location'],
                'language': data['language'],
                'utm_url': data['utm_url'],
                'utm_medium': data['utm_medium'],
                'utm_campaign': data['utm_campaign'],
                'utm_content': None,
                'utm_source': data['utm_source'],
                'referral_key': data['referral_key'],
                'gclid': data['gclid'],
                'tags': data['tags'],
                'automations': data['automations'],
                'street_address': data['street_address'],
                'country': data['country'],
                'city': data['city'],
                'latitude': json['latitude'],
                'longitude': json['longitude'],
                'state': data['state'],
                'zip_code': data['zip_code'],
                'browser_lang': data['browser_lang'],
                'storage_status': data['storage_status'],
                'lead_type': data['lead_type'],
                'deal_status': data['deal_status'],
                'sentiment': data['sentiment'],
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': 1,
                'user': None,
                'tag_objects': [],
                'lead_generation_app': None,
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': json['fb_leadgen_id'],
            'fb_page_id': json['fb_page_id'],
            'fb_form_id': json['fb_form_id'],
            'fb_adgroup_id': json['fb_adgroup_id'],
            'fb_ad_id': json['fb_ad_id'],
            'first_name': json['first_name'],
            'last_name': json['last_name'],
            'email': json['email'],
            'phone': json['phone'],
            'course': json['course'],
            'client_comments': json['client_comments'],
            'current_download': json['current_download'],
            'location': json['location'],
            'language': json['language'],
            'utm_url': json['utm_url'],
            'utm_medium': json['utm_medium'],
            'utm_campaign': json['utm_campaign'],
            'utm_source': json['utm_source'],
            'utm_content': json['utm_content'],
            'referral_key': json['referral_key'],
            'gclid': json['gclid'],
            'tags': json['tags'],
            'automations': json['automations'],
            'street_address': json['street_address'],
            'country': json['country'],
            'city': json['city'],
            'latitude': float(json['latitude']),
            'longitude': float(json['longitude']),
            'state': json['state'],
            'zip_code': json['zip_code'],
            'browser_lang': json['browser_lang'],
            'storage_status': json['storage_status'],
            'lead_type': json['lead_type'],
            'deal_status': json['deal_status'],
            'sentiment': json['sentiment'],
            'academy_id': 1,
            'user_id': None,
            'ac_contact_id': json['ac_contact_id'],
            'ac_deal_id': json['ac_deal_id'],
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': json['won_at']
        }])

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__with__data_active_campaign_slug_priority(self):
        """Test /cohort/:id/user without auth"""
        model1 = self.generate_models(academy=True, academy_kwargs={'active_campaign_slug': 'midgard'})
        model2 = self.generate_models(academy=True,
                                      academy_alias=True,
                                      academy_alias_kwargs={'active_campaign_slug': 'midgard'})

        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        data['phone'] = '123456789'
        data['language'] = 'en'
        data['location'] = 'midgard'

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': data['fb_leadgen_id'],
                'fb_page_id': data['fb_page_id'],
                'fb_form_id': data['fb_form_id'],
                'fb_adgroup_id': data['fb_adgroup_id'],
                'fb_ad_id': data['fb_ad_id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone'],
                'course': data['course'],
                'client_comments': data['client_comments'],
                'current_download': data['current_download'],
                'location': data['location'],
                'language': data['language'],
                'utm_url': data['utm_url'],
                'utm_medium': data['utm_medium'],
                'utm_campaign': data['utm_campaign'],
                'utm_content': None,
                'utm_source': data['utm_source'],
                'referral_key': data['referral_key'],
                'gclid': data['gclid'],
                'tags': data['tags'],
                'automations': data['automations'],
                'street_address': data['street_address'],
                'country': data['country'],
                'city': data['city'],
                'latitude': json['latitude'],
                'longitude': json['longitude'],
                'state': data['state'],
                'zip_code': data['zip_code'],
                'browser_lang': data['browser_lang'],
                'storage_status': data['storage_status'],
                'lead_type': data['lead_type'],
                'deal_status': data['deal_status'],
                'sentiment': data['sentiment'],
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': 2,
                'user': None,
                'lead_generation_app': None,
                'tag_objects': [],
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': json['fb_leadgen_id'],
            'fb_page_id': json['fb_page_id'],
            'fb_form_id': json['fb_form_id'],
            'fb_adgroup_id': json['fb_adgroup_id'],
            'fb_ad_id': json['fb_ad_id'],
            'first_name': json['first_name'],
            'last_name': json['last_name'],
            'email': json['email'],
            'phone': json['phone'],
            'course': json['course'],
            'client_comments': json['client_comments'],
            'current_download': json['current_download'],
            'location': json['location'],
            'language': json['language'],
            'utm_url': json['utm_url'],
            'utm_medium': json['utm_medium'],
            'utm_campaign': json['utm_campaign'],
            'utm_content': json['utm_content'],
            'utm_source': json['utm_source'],
            'referral_key': json['referral_key'],
            'gclid': json['gclid'],
            'tags': json['tags'],
            'automations': json['automations'],
            'street_address': json['street_address'],
            'country': json['country'],
            'city': json['city'],
            'latitude': float(json['latitude']),
            'longitude': float(json['longitude']),
            'state': json['state'],
            'zip_code': json['zip_code'],
            'browser_lang': json['browser_lang'],
            'storage_status': json['storage_status'],
            'lead_type': json['lead_type'],
            'deal_status': json['deal_status'],
            'sentiment': json['sentiment'],
            'academy_id': 2,
            'user_id': None,
            'ac_contact_id': json['ac_contact_id'],
            'ac_deal_id': json['ac_deal_id'],
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': json['won_at']
        }])

    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=Fake_Recaptcha()),
    )
    def test_lead__create_lead(self):
        """Test /lead with create lead happening"""

        model1 = self.generate_models(academy=True, academy_kwargs={'active_campaign_slug': 'midgard'})
        model2 = self.generate_models(academy=True,
                                      academy_alias=True,
                                      academy_alias_kwargs={'active_campaign_slug': 'midgard'})

        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        data['phone'] = '123456789'
        data['language'] = 'en'
        data['location'] = 'midgard'

        response = self.client.post(url, data)
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        self.assertEqual(
            json, {
                'id': 1,
                'fb_leadgen_id': data['fb_leadgen_id'],
                'fb_page_id': data['fb_page_id'],
                'fb_form_id': data['fb_form_id'],
                'fb_adgroup_id': data['fb_adgroup_id'],
                'fb_ad_id': data['fb_ad_id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone'],
                'course': data['course'],
                'client_comments': data['client_comments'],
                'current_download': data['current_download'],
                'location': data['location'],
                'language': data['language'],
                'utm_url': data['utm_url'],
                'utm_medium': data['utm_medium'],
                'utm_campaign': data['utm_campaign'],
                'utm_content': None,
                'utm_source': data['utm_source'],
                'referral_key': data['referral_key'],
                'gclid': data['gclid'],
                'tags': data['tags'],
                'automations': data['automations'],
                'street_address': data['street_address'],
                'country': data['country'],
                'city': data['city'],
                'latitude': json['latitude'],
                'longitude': json['longitude'],
                'state': data['state'],
                'zip_code': data['zip_code'],
                'browser_lang': data['browser_lang'],
                'storage_status': data['storage_status'],
                'lead_type': data['lead_type'],
                'deal_status': data['deal_status'],
                'sentiment': data['sentiment'],
                'ac_contact_id': None,
                'ac_deal_id': None,
                'ac_expected_cohort': None,
                'won_at': None,
                'contact': None,
                'academy': 2,
                'user': None,
                'lead_generation_app': None,
                'tag_objects': [],
                'automation_objects': []
            })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_form_entry_dict(), [{
            'id': 1,
            'contact_id': None,
            'fb_leadgen_id': json['fb_leadgen_id'],
            'fb_page_id': json['fb_page_id'],
            'fb_form_id': json['fb_form_id'],
            'fb_adgroup_id': json['fb_adgroup_id'],
            'fb_ad_id': json['fb_ad_id'],
            'first_name': json['first_name'],
            'last_name': json['last_name'],
            'email': json['email'],
            'phone': json['phone'],
            'course': json['course'],
            'client_comments': json['client_comments'],
            'current_download': json['current_download'],
            'location': json['location'],
            'language': json['language'],
            'utm_url': json['utm_url'],
            'utm_medium': json['utm_medium'],
            'utm_campaign': json['utm_campaign'],
            'utm_content': json['utm_content'],
            'utm_source': json['utm_source'],
            'referral_key': json['referral_key'],
            'gclid': json['gclid'],
            'tags': json['tags'],
            'automations': json['automations'],
            'street_address': json['street_address'],
            'country': json['country'],
            'city': json['city'],
            'latitude': float(json['latitude']),
            'longitude': float(json['longitude']),
            'state': json['state'],
            'zip_code': json['zip_code'],
            'browser_lang': json['browser_lang'],
            'storage_status': json['storage_status'],
            'lead_type': json['lead_type'],
            'deal_status': json['deal_status'],
            'sentiment': json['sentiment'],
            'academy_id': 2,
            'user_id': None,
            'ac_contact_id': json['ac_contact_id'],
            'ac_deal_id': json['ac_deal_id'],
            'ac_expected_cohort': None,
            'lead_generation_app_id': None,
            'won_at': json['won_at']
        }])
