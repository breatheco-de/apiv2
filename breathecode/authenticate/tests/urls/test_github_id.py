"""
Test cases for /user
"""
import urllib
import os
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase
# from ..mocks import GithubRequestsMock


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_github_id_without_url(self):
        """Test /github without auth"""
        url = reverse_lazy('authenticate:github_id', kwargs={'user_id':1})
        response = self.client.get(url)

        data = response.data
        details = data['details']
        status_code = data['status_code']

        self.assertEqual(2, len(data))
        self.assertEqual(details, 'No callback URL specified')
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_github_id_with_args_no_user(self):
        """Test /github"""
        url = reverse_lazy('authenticate:github_id', kwargs={'user_id':2})
        params = {'url': 'https://google.co.ve'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')
        json = response.json()
        expected = {
            'detail': 'user-not-found',
            'status_code': 404
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_github_with_args(self):
        """Test /github"""
        original_url_callback = 'https://google.co.ve'
        url = reverse_lazy('authenticate:github_id', kwargs={'user_id':1})
        params = {'url': 'https://google.co.ve'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')
        params = {
            "client_id": os.getenv('GITHUB_CLIENT_ID', ""),
            "redirect_uri": os.getenv('GITHUB_REDIRECT_URL', "")+f"?url={original_url_callback}&user=1",
            "scope": 'user repo read:org',
        }

        redirect = f'https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}'
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect)