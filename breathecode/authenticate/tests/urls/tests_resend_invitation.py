"""
Test cases for 
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_resend_invite_no_auth(self):
        """Test """
        self.headers(academy=1)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_no_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
                capability='crud_cohort', role='potato', syllabus=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': "You (user: 1) don't have this capability: admissions_developer for "
                    'academy 1','status_code': 403} 
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_with_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
                capability='admissions_developer', role='potato', syllabus=True)
        # print(model['academy'].__dict__)
        # print(self.all_capability_dict())
        # print('academy' in model)
        # print(self.count_academy())
        
        # self.generate_models(authenticate=True, profile_academy=True,
        #     capability='crud_cohort', role='banana')

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1359})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Member not found', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        # self.assertEqual(self.all_user_invite_dict(),[]) # to check what happens in db

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_no_invitation(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
                capability='admissions_developer', role='potato', syllabus=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Invite not found', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_with_invitation(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
                capability='admissions_developer', role='potato', syllabus=True,
                user_invite=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1})
        response = self.client.put(url)
        json = response.json()
        expected = json.copy()
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
