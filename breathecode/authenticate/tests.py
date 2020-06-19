from django.test import TestCase
from django.apps import apps
from django.urls.base import reverse_lazy
from mixer.backend.django import mixer
from django.contrib.auth.models import User, Group
from .models import CredentialsGithub
# Create your tests here.

#@override_settings(STATICFILES_STORAGE=None)
class AuthenticateTestSuite(TestCase):
    """
    Endpoint tests for Invites
    """
    def setUp(self):
        user = mixer.blend('auth.User')
        user.set_password('pass1234')
        user.save()

        params = { "user": user }
        github = mixer.blend('authenticate.CredentialsGithub', **params)
        github.save()

    def test_get_users(self):
        url = reverse_lazy('authenticate:user')
        response = self.client.get(url)
        users = response.json()
        
        # total_users = User.objects.all().count()
        self.assertEqual(1,len(users),"The total users should match the database")


    def test_get_me(self):
        url = reverse_lazy('authenticate:user_me')
        response = self.client.get(url)
        users = response.json()
        
        # total_users = User.objects.all().count()
        self.assertEqual(1,len(users),"I should be able to request my own information using user/me")