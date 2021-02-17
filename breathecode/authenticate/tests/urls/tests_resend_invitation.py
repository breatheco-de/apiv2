"""
Test cases for 
"""
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase
from breathecode.tests.mixins import HeadersMixin


class AuthenticateTestSuite(AuthTestCase, HeadersMixin):
    """Authentication test suite"""
    def test_resend_invite_no_auth(self):
        """Test """
        self.headers(academy=4)

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"member_id":2})
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_resend_invite_with_auth(self):
        """Test """
        self.headers(academy=4)
        self.generate_models(authenticate=True)

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"member_id":2})
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 2) don't have this capability: admissions_developer for "
                    'academy 4','status_code': 403}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        
    def test_resend_invite_with_auth(self):
        """Test """
        self.headers(academy=4)
        self.generate_models(authenticate=True)

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"member_id":2})
        
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': "You (user: 2) don't have this capability: admissions_developer for "
                    'academy 4','status_code': 403}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
