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
from datetime import timedelta, datetime
from django.utils import timezone
from random import choice

class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_user_invite__with_full_name_in_querystring(self):
        """Test academy/user/<int:profileacademy_id>/invite """
        self.headers(academy=1)
        user_invite_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
            }
        profile_academy_kwargs = {
                'email': choice(['a@a.com', 'b@b.com', 'c@c.com']),
                'first_name': choice(['Rene', 'Albert', 'Immanuel']),
                'last_name': choice(['Descartes', 'Camus', 'Kant']),
            }
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_invite', role='potato', user_invite=True,
            user_invite_kwargs=user_invite_kwargs, profile_academy_kwargs=user_invite_kwargs)

        print("FFFFFF", model)

        # id = profile_academy_kwargs.get('id')
        firt_name = user_invite_kwargs.get('first_name')
        last_name = user_invite_kwargs.get('last_name')

        base_url = reverse_lazy('authenticate:user_invite', kwargs={'profileacademy_id': 1})
        url = f'{base_url}?like={firt_name} {last_name}'

        print(url)

        response = self.client.get(url)
        json = response.json()

        expected = {
            'detail': "You (user: 1) don't have this[55 chars] 403"
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_profile_academy_dict(), [{
            
        }])
