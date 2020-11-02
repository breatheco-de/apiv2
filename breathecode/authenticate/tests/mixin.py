"""
Collections of mixins used to login in authorize microservice
"""
import os
import base64
import urllib
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient
from mixer.backend.django import mixer
from pprint import pprint


class DevelopmentEnvironment():
    def __init__(self):
        os.environ['ENV'] = 'development'


class SlackTestCase(APITestCase, DevelopmentEnvironment):
    """APITestCase with Slack methods"""
    url_callback = 'https://google.co.ve'
    academy = None

    def slack(self):
        """Get /slack"""
        url = reverse_lazy('authenticate:slack')
        params = {
            'url': base64.b64encode(self.url_callback.encode("utf-8")),
            'user': 1,
            'a': self.academy
        }
        return self.client.get(f'{url}?{urllib.parse.urlencode(params)}')

    def get_academy(self):
        """Generate a academy with mixer"""
        academy = mixer.blend('admissions.Academy')
        academy.save()
        self.academy = academy


class AuthTestCase(APITestCase):
    """APITestCase with auth methods"""
     # token = None
    user = None
    email = None
    password = 'pass1234'
    token = None

    def setUp(self):
        """Before each test"""
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

    def login(self, email='', password=''):
        """Login"""
        response = self.create_user(email=email, password=password)

        if 'token' in response.data.keys():
            self.token = str(response.data['token'])
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')

        return response
