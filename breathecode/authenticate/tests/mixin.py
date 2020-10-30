"""
Collections of mixins used to login in authorize microservice
"""
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient
from mixer.backend.django import mixer


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
