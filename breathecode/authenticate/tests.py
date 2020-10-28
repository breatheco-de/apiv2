# from django.test import TestCase
from django.apps import apps
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from rest_framework import status
from mixer.backend.django import mixer
from django.contrib.auth.models import User, Group
from .models import CredentialsGithub, Token
import re

class AuthTestCase(APITestCase):
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

        # self.token = Token.create_temp(user)

        self.email = user.email

        params = { "user": user }
        github = mixer.blend('authenticate.CredentialsGithub', **params)
        github.save()

    def create_user(self, email='', password=''):
        if email == '':
            email = self.email

        if password == '':
            password = self.password

        url = reverse_lazy('authenticate:login')
        data = { 'email': email, 'password': password }
        return self.client.post(url, data)

    def force_login(self):
        self.client.force_login(self.user)

    # Create your tests here.
    def login(self, email='', password=''):
        """login"""
        response = self.create_user(email=email, password=password)

        if 'token' in response.data.keys():
            self.token = str(response.data['token'])
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

        return response
    
#@override_settings(STATICFILES_STORAGE=None)
class AuthenticateTestSuite(AuthTestCase): # , Aaaaa
    def test_bad_login(self):
        response = self.create_user(email='Konan@naruto.io', password='Pain!$%')

        non_field_errors = response.data['non_field_errors']
        status_code = response.data['status_code']

        self.assertEqual(len(response.data), 2)
        self.assertEqual(non_field_errors, ['Unable to log in with provided credentials.'])
        self.assertEqual(status_code, 400)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_login(self):
        response = self.create_user()
        tokenPattern = re.compile("^[0-9a-zA-Z]{,40}$")

        token = str(response.data['token'])
        user_id = int(response.data['user_id'])
        email = str(response.data['email'])

        self.assertEqual(len(response.data), 3)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(tokenPattern.match(token)), True)
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_token(self):
        """logout test without token"""
        login_response = self.create_user()

        url = reverse_lazy('authenticate:logout')
        # data = { 'email': email, 'password': password }
        # return client.post(url, data)
        response = self.client.get(url)


        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        """logout test"""
        self.login()
        url = reverse_lazy('authenticate:logout')

        response = self.client.get(url)
        message = str(response.data['message'])

        self.assertEqual(len(response.data), 1)
        self.assertEqual(message, 'User tokens successfully deleted')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_without_auth(self):
        """logout test without token"""
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
        """logout test"""
        login_response = self.login()
        token = str(login_response.data['token'])
        tokenPattern = re.compile("^[0-9a-zA-Z]{,40}$")

        url = reverse_lazy('authenticate:token')
        data = { 'email': self.email, 'password': self.password }
        response = self.client.post(url, data)

        token = str(response.data['token'])
        token_type = str(response.data['token_type'])
        expires_at = response.data['expires_at']
        user_id = int(response.data['user_id'])
        email = response.data['email']

        # self.assertEqual(len(response.data), 2)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(tokenPattern.match(token)), True)
        self.assertEqual(token_type, 'temporal')
        # self.assertEqual(expires_at, 'temporal')
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_without_auth(self):
        """logout test without token"""
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
        self.login()
        url = reverse_lazy('authenticate:user')
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
        """logout test without token"""
        url = reverse_lazy('authenticate:user_me')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        response = self.client.post(url, data)


        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me(self):
        self.login()
        url = reverse_lazy('authenticate:user_me')
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

    def test_change_password_without_token(self):
        """logout test without token"""
        password = 'Pain!$%'
        url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
        data = {'password1': password, 'password2': password}
        # return client.post(url, data)
        response = self.client.post(url, data)

        self.assertContains(response, 'Invalid or expired token')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_but_has_less_of_7_characters(self):
        """logout test without token"""
        password = 'Pain!$%'
        url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
        data = {'password1': password, 'password2': 'password'}
        response = self.client.post(url, data)

        self.assertContains(response, 'Ensure this value has at least 8 characters (it has 7)')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_but_passwords_dont_match(self):
        """logout test without token"""
        password = 'Pain!$%Rinnegan'
        url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
        data = {'password1': password, 'password2': 'PainWithoutRinnegan'}
        response = self.client.post(url, data)

        # &#x27; is '
        self.assertContains(response, 'Passwords don&#x27;t match')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_form(self):
        """logout test without token"""
        url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
        response = self.client.get(url)

        self.assertContains(response, '<label for="id_password1">Password1:</label>')
        self.assertContains(response, '<label for="id_password2">Password2:</label>')
        self.assertContains(response, '<input type="password" name="password1"')
        self.assertContains(response, '<input type="password" name="password2"')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password(self):
        """logout test without token"""
        self.login()
        url_token = reverse_lazy('authenticate:token')
        data_token = { 'email': self.email, 'password': self.password }
        response_token = self.client.post(url_token, data_token)
        token = response_token.data['token']

        password = 'Pain!$%Rinnegan'
        url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
        data = {'token': token, 'password1': password, 'password2': password}
        response = self.client.post(url, data)

        self.assertContains(response, 'You password has been reset successfully, you can close this window.')
        self.assertEqual(response.status_code, status.HTTP_200_OK)