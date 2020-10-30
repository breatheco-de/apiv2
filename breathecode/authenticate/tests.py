# from django.test import TestCase
from django.apps import apps
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient, force_authenticate
from rest_framework import status
from mixer.backend.django import mixer
from django.contrib.auth.models import User
from .models import CredentialsGithub, Token
from django.http.response import HttpResponseRedirectBase
import os, json, re, requests, unittest.mock, base64, urllib
# from pytest_mock import MockerFixture, mocker
# from pprint import pprint
# import pytest_mock

# class BlablablaMock(): #HttpResponseRedirectBase

class FakeResponse():
    """Simutate Response to be used by mocks"""
    status_code = 200
    data = {}
    def __init__(self, status_code, data):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

class GithubRequestsMock():
    """Github requests mock"""
    token = "e72e16c7e42f292c6912e7710c838347ae178b4a"
    # class User:
    #     @staticmethod
    @staticmethod
    def user():
        """Static https://api.github.com/user"""
        return FakeResponse(status_code=200, data={
            "login": "jefer94",
            "id": 3018142,
            "node_id": "MDQ6VXNlcjMwMTgxNDI=",
            "avatar_url": "https://avatars2.githubusercontent.com/u/3018142?v=4",
            "gravatar_id": "",
            "url": "https://api.github.com/users/jefer94",
            "html_url": "https://github.com/jefer94",
            "followers_url": "https://api.github.com/users/jefer94/followers",
            "following_url": "https://api.github.com/users/jefer94/following{/other_user}",
            "gists_url": "https://api.github.com/users/jefer94/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/jefer94/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/jefer94/subscriptions",
            "organizations_url": "https://api.github.com/users/jefer94/orgs",
            "repos_url": "https://api.github.com/users/jefer94/repos",
            "events_url": "https://api.github.com/users/jefer94/events{/privacy}",
            "received_events_url": "https://api.github.com/users/jefer94/received_events",
            "type": "User",
            "site_admin": False,
            "name": "Jeferson De Freitas",
            "company": "@chocoland ",
            "blog": "https://www.facebook.com/chocoland.framework",
            "location": "Colombia, Magdalena, Santa Marta, Gaira",
            "email": "jdefreitaspinto@gmail.com",
            "hireable": True,
            "bio": "I am an Computer engineer, Full-stack Developer and React Developer, I likes an API good, the clean code, the good programming practices",
            "twitter_username": None,
            "public_repos": 70,
            "public_gists": 1,
            "followers": 9,
            "following": 5,
            "created_at": "2012-12-11T17:00:30Z",
            "updated_at": "2020-10-29T19:15:13Z",
            "private_gists": 0,
            "total_private_repos": 2,
            "owned_private_repos": 1,
            "disk_usage": 211803,
            "collaborators": 0,
            "two_factor_authentication": False,
            "plan": {
                "name": "free",
                "space": 976562499,
                "collaborators": 0,
                "private_repos": 10000
            }
        })

    @staticmethod
    def user_emails():
        """Static https://api.github.com/user/emails"""
        return FakeResponse(status_code=200, data=[
            {
                "email": "jeferson-94@hotmail.com",
                "primary": False,
                "verified": True,
                "visibility": None
            },
            {
                "email": "jdefreitaspinto@gmail.com",
                "primary": True,
                "verified": True,
                "visibility": "public"
            }
        ])

    @staticmethod
    def access_token():
        """Static https://github.com/login/oauth/access_token"""
        return FakeResponse(status_code=200, data={
            "access_token": GithubRequestsMock.token,
            "scope": "repo,gist",
            "token_type": "bearer"
        })

    @staticmethod
    def apply_get_requests_mock():
        """Apply get requests mock"""
        return unittest.mock.Mock(side_effect = lambda k, headers : {
            'https://api.github.com/user': GithubRequestsMock.user(),
            'https://api.github.com/user/emails' : GithubRequestsMock.user_emails()
        }.get(k, 'unhandled request %s'%k))

    @staticmethod
    def apply_post_requests_mock():
        """Apply get requests mock"""
        return unittest.mock.Mock(side_effect = lambda k, data, headers : {
            'https://github.com/login/oauth/access_token': GithubRequestsMock.access_token()
        }.get(k, 'unhandled request %s'%k))

class AuthTestCase(APITestCase):
    """APITestCase with auth methods"""
     # token = None
    user = None
    email = None
    password = 'pass1234'
    token = None
    """
    Endpoint tests for Invites
    """
    def setUp(self):
        user = mixer.blend('auth.User')
        user.set_password(self.password)
        user.save()

        self.user = user
        self.email = user.email
        self.client = APIClient()

        params = { "user": user }
        github = mixer.blend('authenticate.CredentialsGithub', **params)
        github.save()

    def create_user(self, email='', password=''):
        """Get login response"""
        if email == '':
            email = self.email

        if password == '':
            password = self.password

        url = reverse_lazy('authenticate:login')
        data = { 'email': email, 'password': password }
        return self.client.post(url, data)

    # Create your tests here.
    def login(self, email='', password=''):
        """Login"""
        response = self.create_user(email=email, password=password)

        if 'token' in response.data.keys():
            self.token = str(response.data['token'])
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

        return response
    
class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    # TODO bad password

    def test_bad_login(self):
        """Test /login with incorrect credentials"""
        response = self.create_user(email='Konan@naruto.io', password='Pain!$%')

        non_field_errors = response.data['non_field_errors']
        status_code = response.data['status_code']

        self.assertEqual(len(response.data), 2)
        self.assertEqual(non_field_errors, ['Unable to log in with provided credentials.'])
        self.assertEqual(status_code, 400)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_login(self):
        """Test /login"""
        response = self.create_user()
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        token = str(response.data['token'])
        user_id = int(response.data['user_id'])
        email = str(response.data['email'])

        self.assertEqual(len(response.data), 3)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(token_pattern.match(token)), True)
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_token(self):
        """Test /logout without token"""
        self.create_user()

        url = reverse_lazy('authenticate:logout')
        response = self.client.get(url)


        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        """Test /logout"""
        url = reverse_lazy('authenticate:logout')

        self.client.force_authenticate(user=self.user)

        response = self.client.get(url)
        print('====', response.data)
        message = str(response.data['message'])

        self.assertEqual(len(response.data), 1)
        self.assertEqual(message, 'User tokens successfully deleted')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_without_auth(self):
        """Test /logout without auth"""
        url = reverse_lazy('authenticate:token')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        response = self.client.post(url, data)


        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token(self):
        """Test /token"""
        login_response = self.login()
        token = str(login_response.data['token'])
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        url = reverse_lazy('authenticate:token')
        data = { 'email': self.email, 'password': self.password }
        response = self.client.post(url, data)

        token = str(response.data['token'])
        token_type = str(response.data['token_type'])
        expires_at = response.data['expires_at'] # test it
        user_id = int(response.data['user_id'])
        email = response.data['email']

        # self.assertEqual(len(response.data), 2)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(token_pattern.match(token)), True)
        self.assertEqual(token_type, 'temporal')
        # self.assertEqual(expires_at, 'temporal')
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_without_auth(self):
        """Test /token without auth"""
        url = reverse_lazy('authenticate:user')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        response = self.client.post(url, data)


        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_users(self):
        """Test /users"""
        # self.login()
        url = reverse_lazy('authenticate:user')

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        users = response.data
        id = users[0]['id']
        email = users[0]['email']
        first_name = users[0]['first_name']
        last_name = users[0]['last_name']
        github = users[0]['github']

        self.assertEqual(1, len(users))
        self.assertEqual(5, len(users[0]))
        self.assertEqual(id, self.user.id)
        self.assertEqual(email, self.user.email)
        self.assertEqual(first_name, self.user.first_name)
        self.assertEqual(last_name, self.user.last_name)
        self.assertEqual(github, {'avatar_url': None, 'name': None})

    def test_user_me_without_auth(self):
        """Test /user/me without auth"""
        url = reverse_lazy('authenticate:user_me')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        # self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me(self):
        """Test /user/me"""
        # self.login()
        url = reverse_lazy('authenticate:user_me')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        user = response.data
        id = user['id']
        email = user['email']
        first_name = user['first_name']
        last_name = user['last_name']
        github = user['github']

        self.assertEqual(5, len(user))
        self.assertEqual(id, self.user.id)
        self.assertEqual(email, self.user.email)
        self.assertEqual(first_name, self.user.first_name)
        self.assertEqual(last_name, self.user.last_name)
        self.assertEqual(github, {'avatar_url': None, 'name': None})

    def test_github_without_url(self):
        """Test /github without auth"""
        url = reverse_lazy('authenticate:github')
        response = self.client.get(url)

        data = response.data
        details = data['details']
        status_code = data['status_code']

        self.assertEqual(2, len(data))
        self.assertEqual(details, 'No callback URL specified')
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_github(self):
        """Test /github"""
        original_url_callback = 'https://google.co.ve'
        url = reverse_lazy('authenticate:github')
        params = {'url': 'https://google.co.ve'}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')
        params = {
            "client_id": os.getenv('GITHUB_CLIENT_ID'),
            "redirect_uri": os.getenv('GITHUB_REDIRECT_URL')+"?url="+original_url_callback,
            "scope": 'user repo read:org',
        }

        redirect = f'https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}'

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect)

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

    @unittest.mock.patch('requests.get', GithubRequestsMock.apply_get_requests_mock())
    @unittest.mock.patch('requests.post', GithubRequestsMock.apply_post_requests_mock())
    def test_github_callback(self):
        """Test /github/callback"""
        original_url_callback = 'https://google.co.ve'
        token_pattern = re.compile("^" + original_url_callback.replace('.', r'\.') +
            r"\?token=[0-9a-zA-Z]{,40}$")
        code = 'Konan'

        url = reverse_lazy('authenticate:github_callback')
        params = {'url': original_url_callback, 'code': code}
        response = self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(bool(token_pattern.match(response.url)), True)

    # def test_change_password_without_token(self):
    #     """logout test without token"""
    #     password = 'Pain!$%'
    #     url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
    #     data = {'password1': password, 'password2': password}
    #     # return client.post(url, data)
    #     response = self.client.post(url, data)

    #     self.assertContains(response, 'Invalid or expired token')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_change_password_but_has_less_of_7_characters(self):
    #     """logout test without token"""
    #     password = 'Pain!$%'
    #     url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
    #     data = {'password1': password, 'password2': 'password'}
    #     response = self.client.post(url, data)

    #     self.assertContains(response, 'Ensure this value has at least 8 characters (it has 7)')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_change_password_but_passwords_dont_match(self):
    #     """logout test without token"""
    #     password = 'Pain!$%Rinnegan'
    #     url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
    #     data = {'password1': password, 'password2': 'PainWithoutRinnegan'}
    #     response = self.client.post(url, data)

    #     # &#x27; is '
    #     self.assertContains(response, 'Passwords don&#x27;t match')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_change_password_form(self):
    #     """logout test without token"""
    #     url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
    #     response = self.client.get(url)

    #     self.assertContains(response, '<label for="id_password1">Password1:</label>')
    #     self.assertContains(response, '<label for="id_password2">Password2:</label>')
    #     self.assertContains(response, '<input type="password" name="password1"')
    #     self.assertContains(response, '<input type="password" name="password2"')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    # def test_change_password(self):
    #     """logout test without token"""
    #     self.login()
    #     url_token = reverse_lazy('authenticate:token')
    #     data_token = { 'email': self.email, 'password': self.password }
    #     response_token = self.client.post(url_token, data_token)
    #     token = response_token.data['token']

    #     password = 'Pain!$%Rinnegan'
    #     url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
    #     data = {'token': token, 'password1': password, 'password2': password}
    #     response = self.client.post(url, data)

    #     self.assertContains(response, 'You password has been reset successfully, you can close this window.')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
