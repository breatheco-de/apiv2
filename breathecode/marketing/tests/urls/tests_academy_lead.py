"""
Test /academy/lead
"""
from logging import error
from django.utils import timezone
from datetime import timedelta
import string
from random import choice, choices, randint
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MarketingTestCase


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
        'phone': choice(['123', '456', '789']),
        'course': random_string(),
        'client_comments': random_string(),
        'location': random_string(),
        'language': random_string(),
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
        'latitude': randint(0, 9999),
        'longitude': randint(0, 9999),
        'state': random_string(),
        'zip_code': randint(0, 9999),
        'browser_lang': random_string(),
        'storage_status': choice(['PENDING', 'PERSISTED']),
        'lead_type': choice(['STRONG', 'SOFT', 'DISCOVERY']),
        'deal_status': choice(['WON', 'LOST']),
        'sentiment': choice(['GOOD', 'BAD']),
    }


class CohortUserTestSuite(MarketingTestCase):
    """Test /academy/lead"""
    """
    🔽🔽🔽 Auth
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:academy_lead')
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': 401
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_form_entry_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__without_academy_header(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato')

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail':
            'Missing academy_id parameter expected for the endpoint url or '
            "'Academy' header",
            'status_code':
            403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__without_data(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead')
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 Storage status in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_bad_storage_status_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?storage_status=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_storage_status_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy(
            'marketing:academy_lead'
        ) + f'?storage_status={model.form_entry.storage_status}'
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 Course in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_bad_course_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?course=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_course_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy(
            'marketing:academy_lead') + f'?course={model.form_entry.course}'
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 Location in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_bad_location_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead') + '?location=freyja'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_location_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability='read_lead',
            role='potato',
            form_entry=True,
            form_entry_kwargs=generate_form_entry_kwargs())

        url = reverse_lazy('marketing:academy_lead'
                           ) + f'?location={model.form_entry.location}'
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 Start in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_bad_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead') + '?start=2100-01-01'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_start_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() -
                      timedelta(hours=48)).strftime("%Y-%m-%d")
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        url = reverse_lazy('marketing:academy_lead') + f'?start={query_date}'
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 End in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_bad_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('marketing:academy_lead') + '?end=1900-01-01'
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_end_in_querystring(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        query_date = (timezone.now() +
                      timedelta(hours=48)).strftime("%Y-%m-%d")
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_lead',
                                     role='potato',
                                     form_entry=True)

        url = reverse_lazy('marketing:academy_lead') + f'?end={query_date}'
        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': model.form_entry.country,
            'course': model.form_entry.course,
            'email': model.form_entry.email,
            'first_name': model.form_entry.first_name,
            'gclid': model.form_entry.gclid,
            'id': model.form_entry.id,
            'language': model.form_entry.language,
            'last_name': model.form_entry.last_name,
            'lead_type': model.form_entry.lead_type,
            'location': model.form_entry.location,
            'storage_status': model.form_entry.storage_status,
            'tags': model.form_entry.tags,
            'utm_campaign': model.form_entry.utm_campaign,
            'utm_medium': model.form_entry.utm_medium,
            'utm_source': model.form_entry.utm_source,
            'utm_url': model.form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        }])

    """
    🔽🔽🔽 Bulk delete
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__delete__in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_lead',
                                    role='potato',
                                    academy=True,
                                    active_campaign_academy=True)

        for field in many_fields:
            form_entry_kwargs = generate_form_entry_kwargs()
            model = self.generate_models(form_entry=True,
                                         contact=True,
                                         automation=True,
                                         form_entry_kwargs=form_entry_kwargs,
                                         models=base)

            url = (reverse_lazy('marketing:academy_lead') + f'?{field}=' +
                   str(getattr(model['form_entry'], field)))
            response = self.client.delete(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_form_entry_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__delete__in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_lead',
                                    role='potato',
                                    academy=True,
                                    active_campaign_academy=True)

        for field in many_fields:
            form_entry_kwargs = generate_form_entry_kwargs()
            model1 = self.generate_models(form_entry=True,
                                          contact=True,
                                          automation=True,
                                          form_entry_kwargs=form_entry_kwargs,
                                          models=base)

            form_entry_kwargs = generate_form_entry_kwargs()
            model2 = self.generate_models(form_entry=True,
                                          contact=True,
                                          automation=True,
                                          form_entry_kwargs=form_entry_kwargs,
                                          models=base)

            url = (reverse_lazy('marketing:academy_lead') + f'?{field}=' +
                   str(getattr(model1['form_entry'], field)) + ',' +
                   str(getattr(model2['form_entry'], field)))
            response = self.client.delete(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_form_entry_dict(), [])

    """
    🔽🔽🔽 Check pagination
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_ten_datas_with_location_with_comma_just_get_100(
            self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_lead',
                                    role='potato')

        models = [
            self.generate_models(form_entry=True, models=base)
            for _ in range(0, 105)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['form_entry'].created_at,
                                reverse=True)

        url = reverse_lazy('marketing:academy_lead')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'country':
            model['form_entry'].country,
            'course':
            model['form_entry'].course,
            'email':
            model['form_entry'].email,
            'first_name':
            model['form_entry'].first_name,
            'gclid':
            None,
            'id':
            model['form_entry'].id,
            'language':
            model['form_entry'].language,
            'last_name':
            model['form_entry'].last_name,
            'lead_type':
            model['form_entry'].lead_type,
            'location':
            model['form_entry'].location,
            'storage_status':
            model['form_entry'].storage_status,
            'tags':
            model['form_entry'].tags,
            'utm_campaign':
            model['form_entry'].utm_campaign,
            'utm_medium':
            model['form_entry'].utm_medium,
            'utm_source':
            model['form_entry'].utm_source,
            'utm_url':
            model['form_entry'].utm_url,
            'created_at':
            self.datetime_to_iso(model['form_entry'].created_at),
        } for model in ordened_models][:100]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_ten_datas_with_location_with_comma_pagination_first_five(
            self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_lead',
                                    role='potato')

        models = [
            self.generate_models(form_entry=True, models=base)
            for _ in range(0, 10)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['form_entry'].created_at,
                                reverse=True)

        url = reverse_lazy('marketing:academy_lead') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            None,
            'next':
            'http://testserver/v1/marketing/academy/lead?limit=5&'
            f'offset=5',
            'previous':
            None,
            'last':
            'http://testserver/v1/marketing/academy/lead?limit=5&'
            f'offset=5',
            'results': [{
                'country':
                model['form_entry'].country,
                'course':
                model['form_entry'].course,
                'email':
                model['form_entry'].email,
                'first_name':
                model['form_entry'].first_name,
                'gclid':
                None,
                'id':
                model['form_entry'].id,
                'language':
                model['form_entry'].language,
                'last_name':
                model['form_entry'].last_name,
                'lead_type':
                model['form_entry'].lead_type,
                'location':
                model['form_entry'].location,
                'storage_status':
                model['form_entry'].storage_status,
                'tags':
                model['form_entry'].tags,
                'utm_campaign':
                model['form_entry'].utm_campaign,
                'utm_medium':
                model['form_entry'].utm_medium,
                'utm_source':
                model['form_entry'].utm_source,
                'utm_url':
                model['form_entry'].utm_url,
                'created_at':
                self.datetime_to_iso(model['form_entry'].created_at),
            } for model in ordened_models][:5],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_ten_datas_with_location_with_comma_pagination_last_five(
            self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_lead',
                                    role='potato')

        models = [
            self.generate_models(form_entry=True, models=base)
            for _ in range(0, 10)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['form_entry'].created_at,
                                reverse=True)

        url = reverse_lazy('marketing:academy_lead') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count':
            10,
            'first':
            'http://testserver/v1/marketing/academy/lead?limit=5',
            'next':
            None,
            'previous':
            'http://testserver/v1/marketing/academy/lead?limit=5',
            'last':
            None,
            'results': [{
                'country':
                model['form_entry'].country,
                'course':
                model['form_entry'].course,
                'email':
                model['form_entry'].email,
                'first_name':
                model['form_entry'].first_name,
                'gclid':
                None,
                'id':
                model['form_entry'].id,
                'language':
                model['form_entry'].language,
                'last_name':
                model['form_entry'].last_name,
                'lead_type':
                model['form_entry'].lead_type,
                'location':
                model['form_entry'].location,
                'storage_status':
                model['form_entry'].storage_status,
                'tags':
                model['form_entry'].tags,
                'utm_campaign':
                model['form_entry'].utm_campaign,
                'utm_medium':
                model['form_entry'].utm_medium,
                'utm_source':
                model['form_entry'].utm_source,
                'utm_url':
                model['form_entry'].utm_url,
                'created_at':
                self.datetime_to_iso(model['form_entry'].created_at),
            } for model in ordened_models][5:],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_ten_datas_with_location_with_comma_pagination_after_last_five(
            self):
        """Test /cohort without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_lead',
                                    role='potato')

        models = [
            self.generate_models(form_entry=True, models=base)
            for _ in range(0, 10)
        ]

        url = reverse_lazy('marketing:academy_lead') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/marketing/academy/lead?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/marketing/academy/lead?limit=5&'
            f'offset=5',
            'last': None,
            'results': [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    """
    🔽🔽🔽 With full like in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_full_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1,
                                 form_entry=True,
                                 models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2,
                                 form_entry=True,
                                 models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.first_name} {models[0].form_entry.last_name}'

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': models[0].form_entry.country,
            'course': models[0].form_entry.course,
            'email': models[0].form_entry.email,
            'first_name': models[0].form_entry.first_name,
            'gclid': models[0].form_entry.gclid,
            'id': models[0].form_entry.id,
            'language': models[0].form_entry.language,
            'last_name': models[0].form_entry.last_name,
            'lead_type': models[0].form_entry.lead_type,
            'location': models[0].form_entry.location,
            'storage_status': models[0].form_entry.storage_status,
            'tags': models[0].form_entry.tags,
            'utm_campaign': models[0].form_entry.utm_campaign,
            'utm_medium': models[0].form_entry.utm_medium,
            'utm_source': models[0].form_entry.utm_source,
            'utm_url': models[0].form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_first_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1,
                                 form_entry=True,
                                 models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2,
                                 form_entry=True,
                                 models=base)
        ]
        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.first_name}'

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': models[0].form_entry.country,
            'course': models[0].form_entry.course,
            'email': models[0].form_entry.email,
            'first_name': models[0].form_entry.first_name,
            'gclid': models[0].form_entry.gclid,
            'id': models[0].form_entry.id,
            'language': models[0].form_entry.language,
            'last_name': models[0].form_entry.last_name,
            'lead_type': models[0].form_entry.lead_type,
            'location': models[0].form_entry.location,
            'storage_status': models[0].form_entry.storage_status,
            'tags': models[0].form_entry.tags,
            'utm_campaign': models[0].form_entry.utm_campaign,
            'utm_medium': models[0].form_entry.utm_medium,
            'utm_source': models[0].form_entry.utm_source,
            'utm_url': models[0].form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_last_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['first_name'] = 'Michael'
        form_entry_kwargs_1['last_name'] = 'Jordan'

        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1,
                                 form_entry=True,
                                 models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2,
                                 form_entry=True,
                                 models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.last_name}'

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': models[0].form_entry.country,
            'course': models[0].form_entry.course,
            'email': models[0].form_entry.email,
            'first_name': models[0].form_entry.first_name,
            'gclid': models[0].form_entry.gclid,
            'id': models[0].form_entry.id,
            'language': models[0].form_entry.language,
            'last_name': models[0].form_entry.last_name,
            'lead_type': models[0].form_entry.lead_type,
            'location': models[0].form_entry.location,
            'storage_status': models[0].form_entry.storage_status,
            'tags': models[0].form_entry.tags,
            'utm_campaign': models[0].form_entry.utm_campaign,
            'utm_medium': models[0].form_entry.utm_medium,
            'utm_source': models[0].form_entry.utm_source,
            'utm_url': models[0].form_entry.utm_url,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_lead__with_email_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    academy=True,
                                    capability='read_lead',
                                    role='potato')

        form_entry_kwargs_1 = generate_form_entry_kwargs()
        form_entry_kwargs_2 = generate_form_entry_kwargs()

        form_entry_kwargs_1['email'] = 'michael@jordan.com'
        models = [
            self.generate_models(form_entry_kwargs=form_entry_kwargs_1,
                                 form_entry=True,
                                 models=base),
            self.generate_models(form_entry_kwargs=form_entry_kwargs_2,
                                 form_entry=True,
                                 models=base)
        ]

        base_url = reverse_lazy('marketing:academy_lead')
        url = f'{base_url}?like={models[0].form_entry.email}'

        response = self.client.get(url)
        json = response.json()

        self.assertDatetime(json[0]['created_at'])
        del json[0]['created_at']

        expected = [{
            'country': models[0].form_entry.country,
            'course': models[0].form_entry.course,
            'email': models[0].form_entry.email,
            'first_name': models[0].form_entry.first_name,
            'gclid': models[0].form_entry.gclid,
            'id': models[0].form_entry.id,
            'language': models[0].form_entry.language,
            'last_name': models[0].form_entry.last_name,
            'lead_type': models[0].form_entry.lead_type,
            'location': models[0].form_entry.location,
            'storage_status': models[0].form_entry.storage_status,
            'tags': models[0].form_entry.tags,
            'utm_campaign': models[0].form_entry.utm_campaign,
            'utm_medium': models[0].form_entry.utm_medium,
            'utm_source': models[0].form_entry.utm_source,
            'utm_url': models[0].form_entry.utm_url,
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_form_entry_dict(), [{
            **self.model_to_dict(model, 'form_entry')
        } for model in models])
