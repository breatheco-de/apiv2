"""
Test /answer/:id
"""
from breathecode.marketing.tasks import persist_single_lead
import re, string, os
from datetime import datetime
from unittest.mock import patch
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

GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)


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
    }


class AnswerIdTestSuite(MarketingTestCase):
    """Test /answer/:id"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_dict_empty(self):
        """Test /answer/:id without auth"""
        try:
            persist_single_lead({})
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'Missing location information')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_bad_location(self):
        """Test /answer/:id without auth"""
        try:
            persist_single_lead({'location': 'they-killed-kenny'})
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message,
                             'No academy found with slug they-killed-kenny')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_location(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True)
        try:
            persist_single_lead({'location': model['academy'].slug})
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message,
                             'You need to specify tags for this entry')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_bad_tags(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True)
        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': 'they-killed-kenny'
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(
                message,
                'Tag applied to the contact not found or has not tag_type assigned'
            )

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_tag_type(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     tag=True,
                                     tag_kwargs={'tag_type': 'STRONG'})
        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(
                message,
                'No automation was specified and the the specified tag has no automation either'
            )

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_automations(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(academy=True,
                                     active_campaign_academy=True,
                                     tag=True,
                                     tag_kwargs={'tag_type': 'STRONG'},
                                     automation=True)
        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': 'they-killed-kenny'
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(
                message,
                'The specified automation they-killed-kenny was not found for this AC Academy'
            )

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_automations_slug(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'The email doesn\'t exist')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_email(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug,
                'email': 'pokemon@potato.io'
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'The first name doesn\'t exist')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_first_name(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug,
                'email': 'pokemon@potato.io',
                'first_name': 'Konan'
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'The last name doesn\'t exist')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_last_name(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug,
                'email': 'pokemon@potato.io',
                'first_name': 'Konan',
                'last_name': 'Amegakure',
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'The phone doesn\'t exist')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_phone(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug,
                'email': 'pokemon@potato.io',
                'first_name': 'Konan',
                'last_name': 'Amegakure',
                'phone': '123123123',
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'The id doesn\'t exist')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_persist_single_lead_with_id(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'})

        try:
            persist_single_lead({
                'location': model['academy'].slug,
                'tags': model['tag'].slug,
                'automations': model['automation'].slug,
                'email': 'pokemon@potato.io',
                'first_name': 'Konan',
                'last_name': 'Amegakure',
                'phone': '123123123',
                'id': 123123123,
            })
            assert False
        except Exception as e:
            message = str(e)
            self.assertEqual(message, 'FormEntry not found (id: 123123123)')

        self.assertEqual(self.count_form_entry(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(OLD_BREATHECODE_PATH['request'],
           apply_old_breathecode_requests_request_mock())
    def test_persist_single_lead_with_form_entry(self):
        """Test /answer/:id without auth"""
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
        mock_old_breathecode.call_args_list = []
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'},
            form_entry=True,
            active_campaign_academy_kwargs={
                'ac_url': 'https://old.hardcoded.breathecode.url'
            })

        persist_single_lead({
            'location': model['academy'].slug,
            'tags': model['tag'].slug,
            'automations': model['automation'].slug,
            'email': 'pokemon@potato.io',
            'first_name': 'Konan',
            'last_name': 'Amegakure',
            'phone': '123123123',
            'id': model['form_entry'].id,
        })

        self.assertEqual(self.all_form_entry_dict(), [{
            'ac_contact_id': '1',
            'ac_deal_id': None,
            'academy_id': 1,
            'automations': '',
            'browser_lang': None,
            'city': None,
            'client_comments': None,
            'contact_id': None,
            'country': None,
            'course': None,
            'deal_status': None,
            'email': None,
            'fb_ad_id': None,
            'fb_adgroup_id': None,
            'fb_form_id': None,
            'fb_leadgen_id': None,
            'fb_page_id': None,
            'first_name': '',
            'gclid': None,
            'id': 1,
            'language': 'en',
            'last_name': '',
            'latitude': None,
            'lead_type': None,
            'location': None,
            'longitude': None,
            'phone': None,
            'referral_key': None,
            'sentiment': None,
            'state': None,
            'storage_status': 'PERSISTED',
            'street_address': None,
            'tags': '',
            'user_id': None,
            'utm_campaign': None,
            'utm_medium': None,
            'utm_source': None,
            'utm_url': None,
            'won_at': None,
            'zip_code': None
        }])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.check_old_breathecode_calls(mock_old_breathecode, model)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(OLD_BREATHECODE_PATH['request'],
           apply_old_breathecode_requests_request_mock())
    @patch(
        REQUESTS_PATH['get'],
        apply_requests_get_mock([(
            200,
            f'https://maps.googleapis.com/maps/api/geocode/json?latlng=15.000000000000000,15.000000000000000&key={GOOGLE_CLOUD_KEY}',
            {
                'status':
                'OK',
                'results': [{
                    'address_components': [{
                        'types': {
                            'country': 'US',
                        },
                        'long_name': 'US',
                    }, {
                        'types': {
                            'locality': 'New York',
                        },
                        'long_name': 'New York',
                    }, {
                        'types': {
                            'route': 'Avenue',
                        },
                        'long_name': 'Avenue',
                    }, {
                        'types': {
                            'postal_code': '10028'
                        },
                        'long_name': '10028',
                    }]
                }]
            })]))
    def test_persist_single_lead_with_form_entry_with_data(self):
        """Test /answer/:id without auth"""
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
        mock_old_breathecode.call_args_list = []
        model = self.generate_models(
            academy=True,
            active_campaign_academy=True,
            tag=True,
            tag_kwargs={'tag_type': 'STRONG'},
            automation=True,
            automation_kwargs={'slug': 'they-killed-kenny'},
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs(),
            active_campaign_academy_kwargs={
                'ac_url': 'https://old.hardcoded.breathecode.url'
            })

        persist_single_lead({
            'location': model['academy'].slug,
            'tags': model['tag'].slug,
            'automations': model['automation'].slug,
            'email': 'pokemon@potato.io',
            'first_name': 'Konan',
            'last_name': 'Amegakure',
            'phone': '123123123',
            'id': model['form_entry'].id,
        })
        form = self.get_form_entry(1)

        self.assertEqual(
            self.all_form_entry_dict(),
            [{
                'ac_contact_id': '1',
                'ac_deal_id': model['form_entry'].ac_deal_id,
                'academy_id': model['form_entry'].academy_id,
                'automations': model['form_entry'].automations,
                'browser_lang': model['form_entry'].browser_lang,
                'city': 'New York',
                'client_comments': model['form_entry'].client_comments,
                'contact_id': model['form_entry'].contact_id,
                'country': 'US',
                'course': model['form_entry'].course,
                'deal_status': model['form_entry'].deal_status,
                'email': model['form_entry'].email,
                'fb_ad_id': model['form_entry'].fb_ad_id,
                'fb_adgroup_id': model['form_entry'].fb_adgroup_id,
                'fb_form_id': model['form_entry'].fb_form_id,
                'fb_leadgen_id': model['form_entry'].fb_leadgen_id,
                'fb_page_id': model['form_entry'].fb_page_id,
                'first_name': model['form_entry'].first_name,
                'gclid': model['form_entry'].gclid,
                'id': model['form_entry'].id,
                'language': model['form_entry'].language,
                'last_name': model['form_entry'].last_name,
                'latitude': form.latitude,
                'lead_type': model['form_entry'].lead_type,
                'location': model['form_entry'].location,
                'longitude': form.longitude,
                'phone': model['form_entry'].phone,
                'referral_key': model['form_entry'].referral_key,
                'sentiment': model['form_entry'].sentiment,
                'state': model['form_entry'].state,
                'storage_status': 'PERSISTED',
                'street_address': 'Avenue',
                'tags': model['form_entry'].tags,
                'user_id': model['form_entry'].user_id,
                'utm_campaign': model['form_entry'].utm_campaign,
                'utm_medium': model['form_entry'].utm_medium,
                'utm_source': model['form_entry'].utm_source,
                'utm_url': model['form_entry'].utm_url,
                'won_at': model['form_entry'].won_at,
                'zip_code': 10028
            }])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.check_old_breathecode_calls(mock_old_breathecode, model)
