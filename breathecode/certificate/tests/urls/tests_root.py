"""
Test /cohort/user
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

class CohortUserTestSuite(CertificateTestCase):
    """Test /cohort/user"""

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
    def test_certificate_re_attemps_with_role_student(self):
        """Test /root with auth"""
        """ Good Request """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, capability='crud_certificate', role='STUDENT', 
            cohort_user=True, syllabus=True, specialty=True, layout_design=True)

        url = reverse_lazy('certificate:root')
        data = [{
            'cohort_slug':  model['cohort'].slug,
            'user_id':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'The certificates have been scheduled for generation'
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_specialty_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_re_attemps_without_cohort_user_and_capability(self):
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
    
    
