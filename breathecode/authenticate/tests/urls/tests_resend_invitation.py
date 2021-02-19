"""
Test cases for 
"""
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase
from breathecode.tests.mixins import HeadersMixin, GenerateModelsMixin


class AuthenticateTestSuite(AuthTestCase, HeadersMixin, GenerateModelsMixin):
    """Authentication test suite"""
    def test_resend_invite_no_auth(self):
        """Test """
        self.headers(academy=4)
        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":2})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_resend_invite_no_capability(self):
        """Test """
        self.headers(academy=4)
        self.headers(capability=4)
        self.generate_models(authenticate=True)

        url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":2})
        
        response = self.client.put(url)
        json = response.json()
        expected = {'detail': "You (user: 2) don't have this [63 chars]", 'status_code': 403} 
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 405)
        
    # def test_resend_invite_with_capability(self):
    #     """Test """
    #     self.headers(academy=4)
    #     self.generate_models(authenticate=True)

    #     url = reverse_lazy('authenticate:academy_resent_invite', kwargs={"user_id":1359})
        
    #     response = self.client.put(url)
    #     json = response.json()
    #     expected = {'detail': "You (user: 2) don't have this[64 chars] 403} != True
    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, 403)
