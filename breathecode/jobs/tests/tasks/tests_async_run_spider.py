"""
Test /answer/:id
"""
from breathecode.jobs.tasks import async_run_spider, run_spider
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
import re, string, os
from datetime import datetime
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from random import choice, choices, randint
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_get_mock,
)
from ..mixins import JobsTestCase


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


@patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
@patch('django.contrib.messages.add_message', MagicMock())
@patch('breathecode.jobs.tasks.async_run_spider', MagicMock())
class AsyncRunSpiderTestSuite(JobsTestCase):
    def test_async_run_spider_no_spider(self):
        """Test /answer/:id without auth"""

        from breathecode.jobs.actions import run_spider

        model = self.generate_models(spider=True)

        async_run_spider(self)
        print(async_run_spider(self))
        assert False

        self.assertEqual(self.async_run_spider(self), 0)

    """Tests action generate_one_certificate"""

    def test_run_spider_with_bad_request(self):
        """generate_one_certificate cant create the certificate"""
        with patch('breathecode.jobs.actions.run_spider') as mock:
            from breathecode.jobs.actions import run_spider
            run_spider()

        self.assertEqual(mock.call_args_list, [call()])

    def test_run_spider_with_bad_request(self):
        """generate_one_certificate cant create the certificate"""
        with patch('breathecode.jobs.actions.run_spider') as mock:
            from breathecode.jobs.actions import run_spider
            # Spider.objects.get(id=args['spi_id'])
            async_run_spider('1')

        self.assertEqual(mock.call_args_list, [call()])

    # """Test /answer/:id"""

    # def test_persist_single_lead_dict_empty(self):
    #     """Test /answer/:id without auth"""
    #     try:
    #         persist_single_lead({})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'Missing location information')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_bad_location(self):
    #     """Test /answer/:id without auth"""
    #     try:
    #         persist_single_lead({'location': 'they-killed-kenny'})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'No academy found with slug they-killed-kenny')

    #     self.assertEqual(self.count_form_entry(), 0)

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

    # def test_persist_single_lead_with_location_academy_alias(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  academy_alias=True,
    #                                  academy_alias_kwargs={'active_campaign_slug': 'odin'})
    #     try:
    #         persist_single_lead({'location': 'odin'})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'You need to specify tags for this entry')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_bad_tags(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True, active_campaign_academy=True)
    #     try:
    #         persist_single_lead({'location': model['academy'].slug, 'tags': 'they-killed-kenny'})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'Tag applied to the contact not found or has not tag_type assigned')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_tag_type(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'})
    #     try:
    #         persist_single_lead({'location': model['academy'].slug, 'tags': model['tag'].slug})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(
    #             message, 'No automation was specified and the the specified tag has no automation either')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_tag_type_automation(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  automation=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'})
    #     try:
    #         persist_single_lead({'location': model['academy'].slug, 'tags': model['tag'].slug})
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, "The email doesn't exist")

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_automations(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True)
    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': 'they-killed-kenny'
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message,
    #                          'The specified automation they-killed-kenny was not found for this AC Academy')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_automations_slug(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'The email doesn\'t exist')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_email(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io'
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'The first name doesn\'t exist')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_first_name(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan'
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'The last name doesn\'t exist')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_last_name(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan',
    #             'last_name': 'Amegakure',
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'The phone doesn\'t exist')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_phone(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan',
    #             'last_name': 'Amegakure',
    #             'phone': '123123123',
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'The id doesn\'t exist')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_id(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(academy=True,
    #                                  active_campaign_academy=True,
    #                                  tag=True,
    #                                  tag_kwargs={'tag_type': 'STRONG'},
    #                                  automation=True,
    #                                  automation_kwargs={'slug': 'they-killed-kenny'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan',
    #             'last_name': 'Amegakure',
    #             'phone': '123123123',
    #             'id': 123123123,
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, 'FormEntry not found (id: 123123123)')

    #     self.assertEqual(self.count_form_entry(), 0)

    # def test_persist_single_lead_with_form_entry(self):
    #     """Test /answer/:id without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
    #     mock_old_breathecode.call_args_list = []
    #     model = self.generate_models(
    #         academy=True,
    #         active_campaign_academy=True,
    #         tag=True,
    #         tag_kwargs={'tag_type': 'STRONG'},
    #         automation=True,
    #         automation_kwargs={'slug': 'they-killed-kenny'},
    #         form_entry=True,
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
    #         'ac_contact_id': '1',
    #         'ac_deal_id': None,
    #         'ac_expected_cohort': None,
    #         'academy_id': 1,
    #         'automations': '',
    #         'browser_lang': None,
    #         'city': None,
    #         'client_comments': None,
    #         'current_download': None,
    #         'contact_id': None,
    #         'country': None,
    #         'course': None,
    #         'deal_status': None,
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
    #         'sentiment': None,
    #         'state': None,
    #         'storage_status': 'PERSISTED',
    #         'street_address': None,
    #         'tags': '',
    #         'user_id': None,
    #         'utm_campaign': None,
    #         'utm_medium': None,
    #         'utm_source': None,
    #         'utm_url': None,
    #         'won_at': None,
    #         'zip_code': None
    #     }])

    #     self.assertEqual(mock_mailgun.call_args_list, [])
    #     self.check_old_breathecode_calls(mock_old_breathecode, model)

    # @patch(
    #     REQUESTS_PATH['get'],
    #     apply_requests_get_mock([(
    #         200,
    #         f'https://maps.googleapis.com/maps/api/geocode/json?latlng=15.000000000000000,15.000000000000000&key={GOOGLE_CLOUD_KEY}',
    #         {
    #             'status': 'INVALID_REQUEST',
    #         })]))
    # def test_persist_single_lead_with_form_entry_with_data_invalid(self):
    #     """Test /answer/:id without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
    #     mock_old_breathecode.call_args_list = []
    #     model = self.generate_models(
    #         academy=True,
    #         active_campaign_academy=True,
    #         tag=True,
    #         tag_kwargs={'tag_type': 'STRONG'},
    #         automation=True,
    #         automation_kwargs={'slug': 'they-killed-kenny'},
    #         form_entry=True,
    #         form_entry_kwargs=generate_form_entry_kwargs(),
    #         active_campaign_academy_kwargs={'ac_url': 'https://old.hardcoded.breathecode.url'})

    #     try:
    #         persist_single_lead({
    #             'location': model['academy'].slug,
    #             'tags': model['tag'].slug,
    #             'automations': model['automation'].slug,
    #             'email': 'pokemon@potato.io',
    #             'first_name': 'Konan',
    #             'last_name': 'Amegakure',
    #             'phone': '123123123',
    #             'id': model['form_entry'].id,
    #         })
    #         assert False
    #     except Exception as e:
    #         message = str(e)
    #         self.assertEqual(message, "'error_message'")

    # @patch(
    #     REQUESTS_PATH['get'],
    #     apply_requests_get_mock([(
    #         200,
    #         f'https://maps.googleapis.com/maps/api/geocode/json?latlng=15.000000000000000,15.000000000000000&key={GOOGLE_CLOUD_KEY}',
    #         {
    #             'status':
    #             'OK',
    #             'results': [{
    #                 'address_components': [{
    #                     'types': {
    #                         'country': 'US',
    #                     },
    #                     'long_name': 'US',
    #                 }, {
    #                     'types': {
    #                         'locality': 'New York',
    #                     },
    #                     'long_name': 'New York',
    #                 }, {
    #                     'types': {
    #                         'route': 'Avenue',
    #                     },
    #                     'long_name': 'Avenue',
    #                 }, {
    #                     'types': {
    #                         'postal_code': '10028'
    #                     },
    #                     'long_name': '10028',
    #                 }]
    #             }]
    #         })]))
    # def test_persist_single_lead_with_form_entry_with_data(self):
    #     """Test /answer/:id without auth"""
    #     mock_mailgun = MAILGUN_INSTANCES['post']
    #     mock_mailgun.call_args_list = []

    #     mock_old_breathecode = OLD_BREATHECODE_INSTANCES['request']
    #     mock_old_breathecode.call_args_list = []
    #     model = self.generate_models(
    #         academy=True,
    #         active_campaign_academy=True,
    #         tag=True,
    #         tag_kwargs={'tag_type': 'STRONG'},
    #         automation=True,
    #         automation_kwargs={'slug': 'they-killed-kenny'},
    #         form_entry=True,
    #         form_entry_kwargs=generate_form_entry_kwargs(),
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
    #     form = self.get_form_entry(1)

    #     self.assertEqual(self.all_form_entry_dict(), [{
    #         'ac_contact_id': '1',
    #         'ac_deal_id': model['form_entry'].ac_deal_id,
    #         'ac_expected_cohort': None,
    #         'academy_id': model['form_entry'].academy_id,
    #         'automations': model['form_entry'].automations,
    #         'browser_lang': model['form_entry'].browser_lang,
    #         'city': 'New York',
    #         'client_comments': model['form_entry'].client_comments,
    #         'current_download': model['form_entry'].current_download,
    #         'contact_id': model['form_entry'].contact_id,
    #         'country': 'US',
    #         'course': model['form_entry'].course,
    #         'deal_status': model['form_entry'].deal_status,
    #         'email': model['form_entry'].email,
    #         'fb_ad_id': model['form_entry'].fb_ad_id,
    #         'fb_adgroup_id': model['form_entry'].fb_adgroup_id,
    #         'fb_form_id': model['form_entry'].fb_form_id,
    #         'fb_leadgen_id': model['form_entry'].fb_leadgen_id,
    #         'fb_page_id': model['form_entry'].fb_page_id,
    #         'first_name': model['form_entry'].first_name,
    #         'gclid': model['form_entry'].gclid,
    #         'id': model['form_entry'].id,
    #         'language': model['form_entry'].language,
    #         'last_name': model['form_entry'].last_name,
    #         'latitude': form.latitude,
    #         'lead_type': model['form_entry'].lead_type,
    #         'location': model['form_entry'].location,
    #         'longitude': form.longitude,
    #         'phone': model['form_entry'].phone,
    #         'referral_key': model['form_entry'].referral_key,
    #         'sentiment': model['form_entry'].sentiment,
    #         'state': model['form_entry'].state,
    #         'storage_status': 'PERSISTED',
    #         'street_address': 'Avenue',
    #         'tags': model['form_entry'].tags,
    #         'user_id': model['form_entry'].user_id,
    #         'utm_campaign': model['form_entry'].utm_campaign,
    #         'utm_medium': model['form_entry'].utm_medium,
    #         'utm_source': model['form_entry'].utm_source,
    #         'utm_url': model['form_entry'].utm_url,
    #         'won_at': model['form_entry'].won_at,
    #         'zip_code': 10028
    #     }])

    #     self.assertEqual(mock_mailgun.call_args_list, [])
    #     self.check_old_breathecode_calls(mock_old_breathecode, model)
