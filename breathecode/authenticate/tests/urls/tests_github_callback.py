"""
Test cases for /user
"""
import re
import urllib
from unittest import mock
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from ...models import Role
from ..mocks import GithubRequestsMock


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_github_callback__without_code(self):
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
    def test_github_callback__user_not_exist(self):
        """Test /github/callback"""
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True, role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile("^" +
                                   original_url_callback.replace('.', r'\.') +
                                   r"\?token=[0-9a-zA-Z]{,40}$")
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        users = [
            x for x in self.all_user_dict()
            if self.assertDatetime(x['date_joined']) and x.pop('date_joined')
        ]

        self.assertEqual(users, [{
            'email': 'jdefreitaspinto@gmail.com',
            'first_name': '',
            'id': 1,
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'last_login': None,
            'last_name': '',
            'password': '',
            'username': 'jdefreitaspinto@gmail.com',
        }])

        self.assertEqual(self.all_credentials_github_dict(), [{
            'avatar_url':
            'https://avatars2.githubusercontent.com/u/3018142?v=4',
            'bio':
            'I am an Computer engineer, Full-stack Developer\xa0and React '
            'Developer, I likes an API good, the clean code, the good programming '
            'practices',
            'blog':
            'https://www.facebook.com/chocoland.framework',
            'company':
            '@chocoland ',
            'email':
            'jdefreitaspinto@gmail.com',
            'github_id':
            3018142,
            'name':
            'Jeferson De Freitas',
            'token':
            'e72e16c7e42f292c6912e7710c838347ae178b4a',
            'twitter_username':
            None,
            'user_id':
            1,
            'username':
            'jefer94'
        }])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True,
                                     user=True,
                                     user_kwargs=user_kwargs,
                                     role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile("^" +
                                   original_url_callback.replace('.', r'\.') +
                                   r"\?token=[0-9a-zA-Z]{,40}$")
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.all_credentials_github_dict(), [{
            'avatar_url':
            'https://avatars2.githubusercontent.com/u/3018142?v=4',
            'bio':
            'I am an Computer engineer, Full-stack Developer\xa0and React '
            'Developer, I likes an API good, the clean code, the good programming '
            'practices',
            'blog':
            'https://www.facebook.com/chocoland.framework',
            'company':
            '@chocoland ',
            'email':
            'jdefreitaspinto@gmail.com',
            'github_id':
            3018142,
            'name':
            'Jeferson De Freitas',
            'token':
            'e72e16c7e42f292c6912e7710c838347ae178b4a',
            'twitter_username':
            None,
            'user_id':
            1,
            'username':
            'jefer94'
        }])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user__with_email_in_uppercase(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True,
                                     user=True,
                                     user_kwargs=user_kwargs,
                                     role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile("^" +
                                   original_url_callback.replace('.', r'\.') +
                                   r"\?token=[0-9a-zA-Z]{,40}$")
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.all_credentials_github_dict(), [{
            'avatar_url':
            'https://avatars2.githubusercontent.com/u/3018142?v=4',
            'bio':
            'I am an Computer engineer, Full-stack Developer\xa0and React '
            'Developer, I likes an API good, the clean code, the good programming '
            'practices',
            'blog':
            'https://www.facebook.com/chocoland.framework',
            'company':
            '@chocoland ',
            'email':
            'jdefreitaspinto@gmail.com',
            'github_id':
            3018142,
            'name':
            'Jeferson De Freitas',
            'token':
            'e72e16c7e42f292c6912e7710c838347ae178b4a',
            'twitter_username':
            None,
            'user_id':
            1,
            'username':
            'jefer94'
        }])
