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

        data = response.json()
        expected = {'detail': 'no-code', 'status_code': 400}

        self.assertEqual(data, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('authenticate.User'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__user_not_exist(self):
        """Test /github/callback"""
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True, role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        users = [
            x for x in self.bc.database.list_of('authenticate.User')
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

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user__with_email_in_uppercase(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True, user=True, user_kwargs=user_kwargs, role_kwargs=role_kwargs)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_bad_user_in_querystring(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True,
                                     user=True,
                                     profile_academy=True,
                                     user_kwargs=user_kwargs,
                                     role_kwargs=role_kwargs,
                                     token=True)

        original_url_callback = 'https://google.co.ve'
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': 'b14f'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')
        json = response.json()
        expected = {'detail': 'token-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])
        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user(self):
        """Test /github/callback"""
        user_kwargs = {'email': 'JDEFREITASPINTO@GMAIL.COM'}
        role_kwargs = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=True,
                                     user=True,
                                     profile_academy=True,
                                     user_kwargs=user_kwargs,
                                     role_kwargs=role_kwargs,
                                     token=True)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        token = self.get_token(1)

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': token}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user_different_email__without_credetials_of_github__without_cohort_user(
            self):
        """Test /github/callback"""
        user = {'email': 'FJOSE123@GMAIL.COM'}
        role = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=role, user=user, profile_academy=True, token=True)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        token = self.get_token(1)

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': token}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
            'jefer94',
        }])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user_different_email__without_credetials_of_github__with_cohort_user(self):
        """Test /github/callback"""
        user = {'email': 'FJOSE123@GMAIL.COM'}
        role = {'slug': 'student', 'name': 'Student'}
        model = self.generate_models(role=role, user=user, profile_academy=True, cohort_user=1, token=True)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        token = self.get_token(1)

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': token}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
            'jefer94',
        }])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user_different_email__with_credentials_of_github__without_cohort_user(
            self):
        """Test /github/callback"""
        users = [{'email': 'FJOSE123@GMAIL.COM'}, {'email': 'jdefreitaspinto@gmail.com'}]
        role = {'slug': 'student', 'name': 'Student'}
        credentials_github = {'github_id': 3018142}
        token = {'user_id': 2}
        model = self.generate_models(role=role,
                                     user=users,
                                     profile_academy=True,
                                     credentials_github=credentials_github,
                                     token=token)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        token = model.token

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': token}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), self.bc.format.to_dict(model.user))

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
            2,
            'username':
            'jefer94',
        }])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy),
        ])

    @mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback__with_user_different_email__with_credentials_of_github__with_cohort_user(self):
        """Test /github/callback"""
        users = [{'email': 'FJOSE123@GMAIL.COM'}, {'email': 'jdefreitaspinto@gmail.com'}]
        role = {'slug': 'student', 'name': 'Student'}
        credentials_github = {'github_id': 3018142}
        token = {'user_id': 2}
        cohort_user = {'user_id': 2}
        model = self.generate_models(role=role,
                                     user=users,
                                     cohort_user=cohort_user,
                                     profile_academy=True,
                                     credentials_github=credentials_github,
                                     token=token)

        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile('^' + original_url_callback.replace('.', r'\.') +
                                   r'\?token=[0-9a-zA-Z]{,40}$')
        code = 'Konan'

        token = model.token

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code, 'user': token}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

        self.assertEqual(self.bc.database.list_of('authenticate.User'), self.bc.format.to_dict(model.user))

        self.assertEqual(self.bc.database.list_of('authenticate.CredentialsGithub'), [{
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
            2,
            'username':
            'jefer94',
        }])

        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [
            self.bc.format.to_dict(model.profile_academy), {
                'academy_id': 1,
                'address': None,
                'email': 'jdefreitaspinto@gmail.com',
                'first_name': model.user[1].first_name,
                'id': 2,
                'last_name': model.user[1].last_name,
                'phone': '',
                'role_id': 'student',
                'status': 'ACTIVE',
                'user_id': 2
            }
        ])
