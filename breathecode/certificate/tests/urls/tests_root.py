"""
Test /certificate
"""
from django.utils import timezone
from datetime import timedelta
from random import choice
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_certificate_test_case import CertificateTestCase

class CertificateTestSuite(CertificateTestCase):
    """Test /certificate"""
    
    """
    🔽🔽🔽 With full like querystring
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_full_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, role='STUDENT',
            capability='read_certificate', user_specialty=True,)

        profile_academy_kwargs = {
                'email':  'b@b.com',
                'first_name': 'Rene',
                'last_name': 'Descartes',
                'status': "INVITED"
            }
        profile_academy_kwargs_2 = {
                'email': 'a@a.com',
                'first_name': 'Michael',
                'last_name': 'Jordan',
                'status': "INVITED"
            }

        model_1 = self.generate_models(cohort=True, user=True, profile_academy=True, 
            cohort_user=True, specialty=True, 
            profile_academy_kwargs=profile_academy_kwargs, models=base)
        model_2 = self.generate_models(cohort=True, user=True, profile_academy=True, 
             cohort_user=True, specialty=True, 
            profile_academy_kwargs=profile_academy_kwargs_2, models=base)

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model_1['academy'].logo_url,
                'name': model_1['academy'].name,
                'slug': model_1['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': model_1['cohort'].name,
                'slug': model_1['cohort'].slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( model_1['user_specialty'].created_at),
            'expires_at': model_1['user_specialty'].expires_at,
            'id': 1,
            'layout': None,
            'preview_url': model_1['user_specialty'].preview_url,
            'signed_by': model_1['user_specialty'].signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model_1['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model_1['specialty'].name,
                'slug': model_1['specialty'].slug,
                'updated_at': self.datetime_to_iso(model_1['specialty'].updated_at),
            },
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' before you can issue any certificates",
            'updated_at': self.datetime_to_iso(model_1['user_specialty'].updated_at),
            'user': {
                'first_name': model_1['user'].first_name, 
                'id': 1, 
                'last_name': model_1['user'].last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_first_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)

        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, user_specialty=True, capability='read_certificate', 
            role="potato", cohort_user=True, specialty=True)

        base_url = reverse_lazy('certificate:root')
        first_name = model['user'].first_name
        url = f'{base_url}?like={first_name}'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': None,
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': model['user_specialty'].signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' before you can issue any certificates",
            'updated_at': self.datetime_to_iso(model['user_specialty'].updated_at),
            'user': {
                'first_name': model['user'].first_name, 
                'id': 1, 
                'last_name': model['user'].last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_last_name_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)

        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, user_specialty=True, capability='read_certificate', 
            role="potato", cohort_user=True, specialty=True)

        base_url = reverse_lazy('certificate:root')
        last_name = model['user'].last_name
        url = f'{base_url}?like={last_name}'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': None,
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': model['user_specialty'].signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' before you can issue any certificates",
            'updated_at': self.datetime_to_iso(model['user_specialty'].updated_at),
            'user': {
                'first_name': model['user'].first_name, 
                'id': 1, 
                'last_name': model['user'].last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate__with_email_in_querystring(self):
        """Test /academy/lead """
        self.headers(academy=1)

        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, user_specialty=True, capability='read_certificate', 
            role="potato", cohort_user=True, specialty=True)

        base_url = reverse_lazy('certificate:root')
        email = model['user'].email
        url = f'{base_url}?like={email}'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': model['academy'].logo_url,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': None,
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': model['user_specialty'].signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' before you can issue any certificates",
            'updated_at': self.datetime_to_iso(model['user_specialty'].updated_at),
            'user': {
                'first_name': model['user'].first_name, 
                'id': 1, 
                'last_name': model['user'].last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)