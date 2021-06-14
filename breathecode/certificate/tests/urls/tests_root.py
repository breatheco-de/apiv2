"""
Test /certificate
"""
import re
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
    🔽🔽🔽 Auth
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_cohort_user__without_auth(self):
        """Test /root without auth"""
        self.headers(academy=1)
        url = reverse_lazy('certificate:root')
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_cohort_user__with_auth_without_permissions(self):
        """Test /root with auth without permissions"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('certificate:root')
        response = self.client.post(url, {})
        json = response.json()

        expected = {
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1",
            'status_code': 403
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    """
    🔽🔽🔽 Post method
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_capability(self):
        """Test /root with auth"""
        """ No capability for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug':  model['cohort'].slug,
            'user_id':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_certificate for academy 1",
            'status_code': 403
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.all_user_specialty_dict(), [])
    

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_cohort_user(self):
        """Test /root with auth"""
        """ No cohort_user for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, role="STUDENT", capability='crud_certificate')

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug':  model['cohort'].slug,
            'user_id':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'student-not-found-in-cohort',
            'status_code': 404
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.all_user_specialty_dict(), [])


    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_user_specialty(self):
        """Test /root with auth"""
        """ No user_specialty for the request"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, role="STUDENT", capability='crud_certificate', 
            cohort_user=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug':  model['cohort'].slug,
            'user_id':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'no-user-specialty',
            'status_code': 404
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.all_user_specialty_dict(), [])

    
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps(self):
        """Test /root with auth"""
        """ Good Request """
        self.headers(academy=1)
        
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, capability='crud_certificate', role='STUDENT', 
            cohort_user=True, syllabus=True, specialty=True, layout_design=True, 
            cohort_stage="ENDED", cohort_user_finantial_status='UP_TO_DATE', 
            cohort_user_educational_status='GRADUATED', user_specialty=True, 
            cohort_finished=True)

        base = model.copy()
        del base['user']
        del base['cohort_user']

        teacher_model = self.generate_models(user=True, cohort_user=True, 
            cohort_user_role='TEACHER', models=base)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug':  model['cohort'].slug,
            'user_id':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']
        del json[0]['signed_by']

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
                'syllabus': {
                    'certificate': {
                        'duration_in_hours': model['certificate'].duration_in_hours
                    }
                }
            },
            'created_at': self.datetime_to_iso( model['user_specialty'].created_at),
            'expires_at': model['user_specialty'].expires_at,
            'id': 1,
            'layout': {
                'name': model['layout_design'].name,
                'slug': model['layout_design'].slug
            },
            'preview_url': model['user_specialty'].preview_url,
            'signed_by_role': 'Director',
            'specialty': {
                'created_at': self.datetime_to_iso(model['specialty'].created_at),
                'id': 1,
                'logo_url': None,
                'name': model['specialty'].name,
                'slug': model['specialty'].slug,
                'updated_at': self.datetime_to_iso(model['specialty'].updated_at),
            },
            'status': 'PENDING',
            'status_text': None,
            'user': {
                'first_name': model['user'].first_name,
                'id': 1,
                'last_name': model['user'].last_name
            }
        }] 

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_specialty_dict(), [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': model['user_specialty'].preview_url,
            'signed_by': teacher_model['user'].first_name + " " +
                teacher_model['user'].last_name,
            'signed_by_role': 'Director',
            'specialty_id': 1,
            'status': 'PERSISTED',
            'status_text':'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'token': "9e76a2ab3bd55454c384e0a5cdb5298d17285949"
        }])
