"""
Test cases for /user
"""
import base64
import urllib
import os
from django.urls.base import reverse_lazy
from rest_framework import status
from .mixin import AuthTestCase
from .mocks import SlackRequestsMock
from pprint import pprint


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_slack_callback_with_error(self):
        """Test /slack/callback without auth"""
        url = reverse_lazy('authenticate:slack_callback')
        params = {'error': 'Oh my god', 'error_description': 'They killed kenny'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        data = response.data
        pprint(data)
        detail = str(data['detail'])
        status_code = data['status_code']

        self.assertEqual(2, len(data))
        self.assertEqual(detail, 'Slack: They killed kenny')
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def test_slack_callback_without_code(self):
    #     """Test /slack/callback without auth"""
    #     url = reverse_lazy('authenticate:slack_callback')
    #     params = {'url': 'https://google.co.ve'}
    #     response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

    #     data = response.data
    #     details = data['details']
    #     status_code = data['status_code']

    #     self.assertEqual(2, len(data))
    #     self.assertEqual(details, 'No github code specified')
    #     self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # @unittest.mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    # @unittest.mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    # def test_slack_callback(self):
    #     """Test /slack/callback"""
    #     original_url_callback = 'https://google.co.ve'
    #     token_pattern = re.compile("^" + original_url_callback.replace('.', r'\.') +
    #         r"\?token=[0-9a-zA-Z]{,40}$")
    #     code = 'Konan'

    #     url = reverse_lazy('authenticate:slack_callback')
    #     params = {'url': original_url_callback, 'code': code}
    #     response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

    #     self.assertEqual(response.status_code, status.HTTP_302_FOUND)
    #     self.assertEqual(bool(token_pattern.match(response.url)), True)

