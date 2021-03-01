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
from datetime import datetime


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
                user_invite=True, token=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1})
        response = self.client.put(url)
        json = response.json()
        token = json['token']
        created = json['created_at']
        sent = json['sent_at']
        del json['sent_at']
        del json['created_at']
        self.assertToken(json['token'])
        del json['token']
        expected = {'status': 'PENDING', 'email': None, 'first_name': None, 'last_name': None}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        print("//////////////1:", self.all_user_invite_dict())
        print("//////////////2:", [
                {'id': model['user_invite'].id, 
                'email': model['user_invite'].email, 
                'academy_id': model['user_invite'].academy_id, 
                'cohort_id': model['user_invite'].cohort_id, 
                'role_id': model['user_invite'].role_id,
                'first_name': model['user_invite'].first_name, 
                'last_name': model['user_invite'].last_name,
                'token': token,
                'author_id': model['user_invite'].author_id,
                'status': model['user_invite'].status,
                'phone': model['user_invite'].phone,
                'sent_at': sent
                }])


        all_user_invite = [x for x in self.all_user_invite_dict() if isinstance(x.sent_at, datetime) and x.pop('sent_at')]
        self.assertEqual(all_user_invite,[
                {'id': model['user_invite'].id, 
                'email': model['user_invite'].email, 
                'academy_id': model['user_invite'].academy_id, 
                'cohort_id': model['user_invite'].cohort_id, 
                'role_id': model['user_invite'].role_id,
                'first_name': model['user_invite'].first_name, 
                'last_name': model['user_invite'].last_name,
                'token': token,
                'author_id': model['user_invite'].author_id,
                'status': model['user_invite'].status,
                'phone': model['user_invite'].phone,
                }
                ])
        
