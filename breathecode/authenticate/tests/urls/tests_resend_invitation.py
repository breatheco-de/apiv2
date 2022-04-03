"""
Test cases for
"""
import os
import re
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    apply_requests_post_mock,
)
from datetime import timedelta, datetime
from django.utils import timezone


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_resend_invite_no_auth(self):
        """Test """
        self.headers(academy=1)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1})

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
        model = self.generate_models(authenticate=True, profile_academy=True, syllabus=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1})

        response = self.client.put(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: invite_resend for "
            'academy 1',
            'status_code': 403
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_with_capability(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True)

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1359})

        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Member not found', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_resend_invite_no_invitation(self):
        """Test """
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1})

        response = self.client.put(url)
        json = response.json()
        created = json['created_at']
        del json['created_at']

        expected = {
            'id': 1,
            'status': 'INVITED',
            'address': None,
            'email': None,
            'email': None,
            'first_name': None,
            'last_name': None,
            'phone': '',
            'invite_url': 'http://localhost:8000/v1/auth/academy/html/invite',
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            },
            'role': {
                'id': 'potato',
                'name': 'potato',
                'slug': 'potato'
            },
            'user': {
                'email': model['user'].email,
                'first_name': model['user'].first_name,
                'github': None,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
                'profile': None
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        all_user_invite = [x for x in self.all_user_invite_dict() if x.pop('sent_at')]
        self.assertEqual(all_user_invite, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('requests.post',
           apply_requests_post_mock([
               (201, f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages", {})
           ]))
    def test_resend_invite_with_invitation(self):
        """Test """
        self.headers(academy=1)
        profile_academy_kwargs = {'email': 'email@dotdotdotdot.dot'}
        user_invite_kwargs = {'email': 'email@dotdotdotdot.dot'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True,
                                     user_invite=True,
                                     profile_academy_kwargs=profile_academy_kwargs,
                                     user_invite_kwargs=user_invite_kwargs)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1})
        response = self.client.put(url)
        json = response.json()
        created = json['created_at']
        sent = json['sent_at']
        del json['sent_at']
        del json['created_at']

        expected = {
            'id': 1,
            'status': 'PENDING',
            'email': 'email@dotdotdotdot.dot',
            'first_name': None,
            'last_name': None,
            'token': model.user_invite.token,
            'invite_url': f'http://localhost:8000/v1/auth/member/invite/{model.user_invite.token}',
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            },
            'role': {
                'id': 'potato',
                'name': 'potato',
                'slug': 'potato'
            },
            'cohort': {
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        all_user_invite = [x for x in self.all_user_invite_dict() if x.pop('sent_at')]
        self.assertEqual(all_user_invite, [{
            'id': model['user_invite'].id,
            'email': model['user_invite'].email,
            'academy_id': model['user_invite'].academy_id,
            'cohort_id': model['user_invite'].cohort_id,
            'role_id': model['user_invite'].role_id,
            'first_name': model['user_invite'].first_name,
            'last_name': model['user_invite'].last_name,
            'token': model['user_invite'].token,
            'author_id': model['user_invite'].author_id,
            'status': model['user_invite'].status,
            'phone': model['user_invite'].phone,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resend_invite_recently(self):
        """Test """
        self.headers(academy=1)
        past_time = timezone.now() - timedelta(seconds=100)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='invite_resend',
                                     role='potato',
                                     syllabus=True,
                                     user_invite=True,
                                     token=True,
                                     user_invite_kwargs={'sent_at': past_time})
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={'pa_id': 1})
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Imposible to resend invitation', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.all_user_invite_dict(),
                         [{
                             **self.model_to_dict(model, 'user_invite'),
                             'sent_at': past_time,
                         }])
