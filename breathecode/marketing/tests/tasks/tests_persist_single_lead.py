"""
Test /answer/:id
"""
from breathecode.marketing.tasks import persist_single_lead
import re
from datetime import datetime
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH, apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock, apply_google_cloud_blob_mock, MAILGUN_PATH,
    MAILGUN_INSTANCES, apply_mailgun_requests_post_mock, OLD_BREATHECODE_PATH,
    OLD_BREATHECODE_INSTANCES, apply_old_breathecode_requests_request_mock)
from ..mixins import MarketingTestCase


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

    # TODO: this tests is stopped because we have other priorities
    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    # @patch(OLD_BREATHECODE_PATH['request'], apply_old_breathecode_requests_request_mock())
    # def test_persist_single_lead_with_form_entry(self):
    #     """Test /answer/:id without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
    #     mock_old_breathecode.call_args_list = []
    #     model = self.generate_models(academy=True, active_campaign_academy=True,
    #         tag=True, tag_kwargs={'tag_type': 'STRONG'}, automation=True,
    #         automation_kwargs={'slug': 'they-killed-kenny'}, form_entry=True,
    #         active_campaign_academy_kwargs={'ac_url': 'https://old.hardcoded.breathecode.url'})

    #     persist_single_lead({
    #         'location': model['academy'].slug,
    #         'tags': model['tag'].slug,
    #         'automations': model['automation'].slug,
    #         'email': 'pokemon@potato.io',
    #         'first_name': 'Konan',
    #         'last_name': 'Amegakure',
    #         'phone': '123123123',
    #         'id': model['form_entry'].id,
    #     })

    #     self.assertEqual(self.all_form_entry_dict(), [{
    #         'ac_academy_id': 1,
    #         'academy_id': 1,
    #         'automations': '',
    #         'browser_lang': None,
    #         'city': None,
    #         'client_comments': None,
    #         'contact_id': None,
    #         'country': None,
    #         'course': None,
    #         'email': None,
    #         'fb_ad_id': None,
    #         'fb_adgroup_id': None,
    #         'fb_form_id': None,
    #         'fb_leadgen_id': None,
    #         'fb_page_id': None,
    #         'first_name': '',
    #         'gclid': None,
    #         'id': 1,
    #         'language': 'en',
    #         'last_name': '',
    #         'latitude': None,
    #         'lead_type': None,
    #         'location': None,
    #         'longitude': None,
    #         'phone': None,
    #         'referral_key': None,
    #         'state': None,
    #         'storage_status': 'PERSISTED',
    #         'street_address': None,
    #         'tags': '',
    #         'utm_campaign': None,
    #         'utm_medium': None,
    #         'utm_source': None,
    #         'utm_url': None,
    #         'zip_code': None
    #     }])

    #     self.assertEqual(mock_mailgun.call_args_list, [])
    #     # self.assertEqual(mock_old_breathecode.call_args_list, [])
    #     self.check_old_breathecode_calls(mock_old_breathecode, model)
