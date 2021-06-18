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

        base = self.generate_models(authenticate=True, cohort=True, cohort_finished=True,
            capability='read_certificate', role='potato', academy=True, profile_academy=True,
            specialty=True)
        
        del base['user']

        user_kwargs = {
            'email':  'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {
            "token": "123dfefef1123rerf346g"
        }
        user_specialty_kwargs_2 = {
            "token": "jojfsdknjbs1123rerf346g"
        }
        models = [
            self.generate_models(user=True, user_specialty=True, cohort_user=True, 
                user_kwargs=user_kwargs, user_specialty_kwargs=user_specialty_kwargs_1, 
                models=base),
            self.generate_models(user=True, user_specialty=True, cohort_user=True,  
                user_kwargs=user_kwargs_2, user_specialty_kwargs=user_specialty_kwargs_2,
                models=base)
        ]       

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name, 
                'id': 2, 
                'last_name': models[0].user.last_name
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
        base = self.generate_models(authenticate=True, cohort=True, cohort_finished=True,
            capability='read_certificate', role='potato', academy=True, profile_academy=True,
            specialty=True)
        
        del base['user']

        user_kwargs = {
            'email':  'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {
            "token": "123dfefef1123rerf346g"
        }
        user_specialty_kwargs_2 = {
            "token": "jojfsdknjbs1123rerf346g"
        }
        models = [
            self.generate_models(user=True, user_specialty=True, cohort_user=True, 
                user_kwargs=user_kwargs, user_specialty_kwargs=user_specialty_kwargs_1, 
                models=base),
            self.generate_models(user=True, user_specialty=True, cohort_user=True,  
                user_kwargs=user_kwargs_2, user_specialty_kwargs=user_specialty_kwargs_2,
                models=base)
        ] 

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name, 
                'id': 2, 
                'last_name': models[0].user.last_name
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
        base = self.generate_models(authenticate=True, cohort=True, cohort_finished=True,
            capability='read_certificate', role='potato', academy=True, profile_academy=True,
            specialty=True)
        
        del base['user']

        user_kwargs = {
            'email':  'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {
            "token": "123dfefef1123rerf346g"
        }
        user_specialty_kwargs_2 = {
            "token": "jojfsdknjbs1123rerf346g"
        }
        models = [
            self.generate_models(user=True, user_specialty=True, cohort_user=True, 
                user_kwargs=user_kwargs, user_specialty_kwargs=user_specialty_kwargs_1, 
                models=base),
            self.generate_models(user=True, user_specialty=True, cohort_user=True,  
                user_kwargs=user_kwargs_2, user_specialty_kwargs=user_specialty_kwargs_2,
                models=base)
        ] 

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name, 
                'id': 2, 
                'last_name': models[0].user.last_name
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
        base = self.generate_models(authenticate=True, cohort=True, cohort_finished=True,
            capability='read_certificate', role='potato', academy=True, profile_academy=True,
            specialty=True)
        
        del base['user']

        user_kwargs = {
            'email':  'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Michael',
            'last_name': 'Jordan',
        }
        user_specialty_kwargs_1 = {
            "token": "123dfefef1123rerf346g"
        }
        user_specialty_kwargs_2 = {
            "token": "jojfsdknjbs1123rerf346g"
        }
        models = [
            self.generate_models(user=True, user_specialty=True, cohort_user=True, 
                user_kwargs=user_kwargs, user_specialty_kwargs=user_specialty_kwargs_1, 
                models=base),
            self.generate_models(user=True, user_specialty=True, cohort_user=True,  
                user_kwargs=user_kwargs_2, user_specialty_kwargs=user_specialty_kwargs_2,
                models=base)
        ] 

        base_url = reverse_lazy('certificate:root')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'academy': {
                'id': 1,
                'logo_url': models[0].academy.logo_url,
                'name': models[0].academy.name,
                'slug': models[0].academy.slug,
                'website_url': None
            },
            'cohort': {
                'id': 1,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
                'syllabus': {}
            },
            'created_at': self.datetime_to_iso( models[0].user_specialty.created_at),
            'expires_at': models[0].user_specialty.expires_at,
            'id': 1,
            'layout': None,
            'preview_url': models[0].user_specialty.preview_url,
            'signed_by': models[0].user_specialty.signed_by,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(models[0].specialty.created_at),
                'id': 1,
                'logo_url': None,
                'name': models[0].specialty.name,
                'slug': models[0].specialty.slug,
                'updated_at': self.datetime_to_iso(models[0].specialty.updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'updated_at': self.datetime_to_iso(models[0].user_specialty.updated_at),
            'user': {
                'first_name': models[0].user.first_name, 
                'id': 2, 
                'last_name': models[0].user.last_name
            }
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)