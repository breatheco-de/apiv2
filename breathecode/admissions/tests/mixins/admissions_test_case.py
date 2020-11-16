"""
Collections of mixins used to login in authorize microservice
"""
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient
from mixer.backend.django import mixer
from breathecode.tests.mixins import DevelopmentEnvironment

class AdmissionsTestCase(APITestCase, DevelopmentEnvironment):
    """AdmissionsTestCase with auth methods"""
     # token = None
    user = None
    password = 'pass1234'
    certificate = None
    academy = None

    def generate_models(self, user=None, authenticate=None, certificate=None, academy=None):
        if user or authenticate:
            user = mixer.blend('auth.User')
            user.set_password(self.password)
            user.save()
            self.user = user

        if authenticate:
            self.client.force_authenticate(user=user)

        if certificate:
            certificate = mixer.blend('admissions.Certificate')
            certificate.save()
            self.certificate = certificate

        if academy:
            academy = mixer.blend('admissions.Academy')
            academy.save()
            self.academy = academy
