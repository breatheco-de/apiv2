"""
Test /academy/lead
"""
from decimal import Decimal
import string
from random import choice, choices, randint
from unittest.mock import patch, MagicMock
from django.urls.base import reverse_lazy
from rest_framework import status
from faker import Faker
from ..mixins import MarketingTestCase

fake = Faker()


def random_string():
    return ''.join(choices(string.ascii_letters, k=10))


def post_serializer(data={}):
    return {
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
        'utm_placement': None,
        'utm_term': None,
        'utm_plan': None,
        'sex': None,
        'custom_fields': None,
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
        'storage_status_text': '',
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
        'automation_objects': [],
        **data,
    }


def form_entry_field(data={}):
    return {
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
        'utm_placement': None,
        'utm_term': None,
        'utm_plan': None,
        'sex': None,
        'custom_fields': None,
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
        'storage_status_text': '',
        'lead_type': None,
        'deal_status': None,
        'sentiment': None,
        'ac_contact_id': None,
        'ac_deal_id': None,
        'ac_expected_cohort': None,
        'won_at': None,
        'contact_id': None,
        'academy_id': None,
        'user_id': None,
        'lead_generation_app_id': None,
        **data,
    }


class FakeRecaptcha:

    class RiskAnalysis:

        def __init__(self, *args, **kwargs):
            self.score = 0.9

    def __init__(self, *args, **kwargs):
        self.risk_analysis = self.RiskAnalysis()


def generate_form_entry_kwargs(data={}):
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
        'zip_code': randint(0, 9999),
        'browser_lang': random_string(),
        'storage_status': choice(['PENDING', 'PERSISTED']),
        'lead_type': choice(['STRONG', 'SOFT', 'DISCOVERY']),
        'deal_status': choice(['WON', 'LOST']),
        'sentiment': choice(['GOOD', 'BAD']),
        'current_download': random_string(),
        **data,
    }


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Passing nothing
    """

    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_lead__without_data(self):
        url = reverse_lazy('marketing:lead')

        response = self.client.post(url, format='json')
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        expected = post_serializer()

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('marketing.FormEntry'), [
            form_entry_field({
                'id': 1,
                'academy_id': None,
                'storage_status_text': 'Missing location information',
            })
        ])

    """
    🔽🔽🔽 Validations of fields
    """

    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_lead__with__bad_data(self):
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs()
        response = self.client.post(url, data, format='json')

        json = response.json()
        expected = {
            'phone': ["Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."],
            'language': ['Ensure this field has no more than 2 characters.']
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Passing required fields
    """

    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_lead__with__data(self):
        url = reverse_lazy('marketing:lead')

        data = generate_form_entry_kwargs({
            'phone': '123456789',
            'language': 'en',
        })

        response = self.client.post(url, data, format='json')
        json = response.json()

        self.assertDatetime(json['created_at'])
        self.assertDatetime(json['updated_at'])
        del json['created_at']
        del json['updated_at']

        expected = post_serializer({
            **data,
            'id': 1,
            'academy': None,
            'latitude': self.bc.format.to_decimal_string(data['latitude']),
            'longitude': self.bc.format.to_decimal_string(data['longitude']),
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('marketing.FormEntry'), [
            form_entry_field({
                **data,
                'id': 1,
                'academy_id': None,
                'latitude': Decimal(data['latitude']),
                'longitude': Decimal(data['longitude']),
                'storage_status_text': f"No academy found with slug {data['location']}",
            })
        ])

    """
    🔽🔽🔽 Passing slug of Academy or AcademyAlias
    """

    @patch.multiple(
        'breathecode.services.google_cloud.Recaptcha',
        __init__=MagicMock(return_value=None),
        create_assessment=MagicMock(return_value=FakeRecaptcha()),
    )
    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_passing_slug_of_academy_or_academy_alias(self):
        cases = [
            ({
                'slug': 'midgard'
            }, None),
            ({
                'slug': 'midgard'
            }, 1),
            (1, {
                'active_campaign_slug': 'midgard'
            }),
        ]

        for academy, academy_alias in cases:
            model = self.generate_models(academy=academy, academy_alias=academy_alias)
            url = reverse_lazy('marketing:lead')

            data = generate_form_entry_kwargs({
                'phone': '123456789',
                'language': 'en',
                'location': 'midgard',
            })

            response = self.client.post(url, data, format='json')
            json = response.json()

            self.assertDatetime(json['created_at'])
            self.assertDatetime(json['updated_at'])
            del json['created_at']
            del json['updated_at']

            expected = post_serializer({
                **data,
                'id': model.academy.id,
                'academy': model.academy.id,
                'latitude': self.bc.format.to_decimal_string(data['latitude']),
                'longitude': self.bc.format.to_decimal_string(data['longitude']),
            })

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.bc.database.list_of('marketing.FormEntry'), [
                form_entry_field({
                    **data,
                    'id': model.academy.id,
                    'academy_id': model.academy.id,
                    'latitude': Decimal(data['latitude']),
                    'longitude': Decimal(data['longitude']),
                    'storage_status_text': 'No academy found with slug midgard',
                })
            ])

            # teardown
            self.bc.database.delete('admissions.Academy')
            self.bc.database.delete('marketing.AcademyAlias')
            self.bc.database.delete('marketing.FormEntry')
