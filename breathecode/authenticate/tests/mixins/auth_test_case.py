"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.authenticate.models import ProfileAcademy
from unittest.mock import patch
from django.contrib.auth.models import User
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase, APIClient
from mixer.backend.django import mixer
from django.core.cache import cache
from breathecode.tests.mixins import ModelsMixin
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)


class AuthTestCase(APITestCase, ModelsMixin):
    """APITestCase with auth methods"""

    # token = None
    user = None
    email = None
    password = "pass1234"
    token = None

    def setUp(self):
        """Before each test"""
        cache.clear()

        user = mixer.blend("auth.User")
        user.set_password(self.password)
        user.save()

        self.user = user
        self.email = user.email
        self.client = APIClient()

        params = {"user": user}
        github = mixer.blend("authenticate.CredentialsGithub", **params)
        github.save()

    def create_user(self, email="", password=""):
        """Get login response"""
        if email == "":
            email = self.email

        if password == "":
            password = self.password

        url = reverse_lazy("authenticate:login")
        data = {"email": email, "password": password}
        return self.client.post(url, data)

    def login(self, email="", password=""):
        """Login"""
        response = self.create_user(email=email, password=password)

        if "token" in response.data.keys():
            self.token = str(response.data["token"])
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

        return response

    def all_profile_academy_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in ProfileAcademy.objects.filter()]

    def get_profile_academy(self, id: int):
        return ProfileAcademy.objects.filter(id=id).first()

    def headers(self, **kargs):
        headers = {}

        items = [
            index
            for index in kargs
            if kargs[index] and (isinstance(kargs[index], str) or isinstance(kargs[index], int))
        ]

        for index in items:
            headers[f"HTTP_{index.upper()}"] = str(kargs[index])

        self.client.credentials(**headers)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def generate_models(
        self,
        authenticate=False,
        user=False,
        academy=False,
        profile_academy=False,
        role="",
        capability="",
        profile_academy_status="",
        credentials_github=False,
        profile=False,
        profile_kwargs={},
        github_academy_user={},
        models={},
    ):
        """Generate models"""
        # TODO: rewrite authenticate tests to use the global generate_models
        self.maxDiff = None
        models = models.copy()

        if not "user" in models and (user or authenticate or profile_academy or credentials_github):
            models["user"] = mixer.blend("auth.User")
            models["user"].set_password(self.password)
            models["user"].save()

        if not "profile" in models and profile:
            kargs = {}

            if "user" in models:
                kargs["user"] = models["user"]

            kargs = {**kargs, **profile_kwargs}
            models["profile"] = mixer.blend("authenticate.Profile", **kargs)

        if not "credentials_github" in models and credentials_github:
            kargs = {"user": models["user"]}

            models["credentials_github"] = mixer.blend("authenticate.CredentialsGithub", **kargs)

        if authenticate:
            self.client.force_authenticate(user=models["user"])

        if not "academy" in models and (academy or profile_academy):
            models["academy"] = mixer.blend("admissions.Academy")

        if not "capability" in models and capability:
            kargs = {
                "slug": capability,
                "description": capability,
            }

            models["capability"] = mixer.blend("authenticate.Capability", **kargs)

        if not "role" in models and role:
            kargs = {
                "slug": role,
                "name": role,
                "capabilities": [models["capability"]],
            }

            models["role"] = mixer.blend("authenticate.Role", **kargs)

        if not "profile_academy" in models and profile_academy:
            kargs = {}

            if user or authenticate:
                kargs["user"] = models["user"]
                kargs["academy"] = models["academy"]
                kargs["role"] = models["role"]

            if profile_academy_status:
                kargs["status"] = profile_academy_status

            models["profile_academy"] = mixer.blend("authenticate.ProfileAcademy", **kargs)

        return models
