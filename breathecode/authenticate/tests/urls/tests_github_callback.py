"""
Test cases for /user
"""
import re
import urllib
from unittest import mock
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase
from ...models import Role
from ..mocks import GithubRequestsMock


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_github_callback_without_code(self):
        """Test /github/callback without auth"""
        url = reverse_lazy('authenticate:github_callback')
        params = {'url': 'https://google.co.ve'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        data = response.data
        details = data['details']
        status_code = data['status_code']

        self.assertEqual(2, len(data))
        self.assertEqual(details, 'No github code specified')
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback(self):
        """Test /github/callback"""
        role = Role(slug='student', name="Student")
        role.save()

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile("^" + original_url_callback.replace('.', r'\.') +
            r"\?token=[0-9a-zA-Z]{,40}$")
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)
