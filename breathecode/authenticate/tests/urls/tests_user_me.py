"""
Test cases for /user
"""

import datetime

import pytz
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase


def get_permission_serializer(permission):
    return {
        "codename": permission.codename,
        "name": permission.name,
    }


def user_setting_serializer(user_setting):
    return {
        "lang": user_setting.lang,
        "main_currency": user_setting.main_currency,
    }


def get_serializer(
    self, user, credentials_github=None, profile_academies=[], profile=None, permissions=[], user_setting=None, data={}
):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": self.bc.datetime.to_iso_string(user.date_joined),
        "username": user.username,
        "settings": user_setting_serializer(user_setting) if user_setting else None,
        "permissions": [get_permission_serializer(x) for x in permissions],
        "github": (
            {
                "avatar_url": credentials_github.avatar_url,
                "name": credentials_github.name,
                "username": credentials_github.username,
            }
            if credentials_github
            else None
        ),
        "profile": (
            {
                "avatar_url": profile.avatar_url,
            }
            if profile
            else None
        ),
        "roles": [
            {
                "academy": {
                    "id": profile_academy.academy.id,
                    "name": profile_academy.academy.name,
                    "slug": profile_academy.academy.slug,
                    "timezone": profile_academy.academy.timezone,
                },
                "created_at": self.bc.datetime.to_iso_string(profile_academy.created_at),
                "id": profile_academy.id,
                "role": profile_academy.role.slug,
            }
            for profile_academy in profile_academies
        ],
        **data,
    }


class AuthenticateTestSuite(AuthTestCase):

    def setUp(self):
        super().setUp()

        Permission = self.bc.database.get_model("auth.Permission")
        permission = Permission.objects.filter().order_by("-id").first()
        self.latest_permission_id = permission.id

    """
    🔽🔽🔽 Auth
    """

    def test_user_me__without_auth(self):
        """Test /user/me without auth"""
        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Authentication credentials were not provided.",
            "status_code": status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Get
    """

    def test_user_me(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with CredentialsGithub
    """

    def test_user_me__with_github_credentials(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, credentials_github=True)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            credentials_github=model.credentials_github,
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with ProfileAcademy
    """

    def test_user_me__with_profile_academy(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile_academy=True)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile_academies=[model.profile_academy],
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with Profile
    """

    def test_user_me__with_profile(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile=True)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile=model.profile,
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with Profile and Permission
    """

    def test_user_me__with_profile__with_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile=True, permission=1)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile=model.profile,
            permissions=[],
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with Profile and Permission
    """

    def test_user_me__with_profile__one_group_with_one_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile=True, permission=1, group=1)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile=model.profile,
            permissions=[model.permission],
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with Profile and three Group with one Permission
    """

    def test_user_me__with_profile__three_groups_with_one_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile=True, permission=1, group=3)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile=model.profile,
            permissions=[model.permission],
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with Profile and two Group with four Permission
    """

    def test_user_me__with_profile__two_groups_with_four_permissions(self):
        """Test /user/me"""

        groups = [
            {
                "permissions": [self.latest_permission_id + 1, self.latest_permission_id + 2],
            },
            {
                "permissions": [self.latest_permission_id + 3, self.latest_permission_id + 4],
            },
        ]
        model = self.generate_models(authenticate=True, profile=True, permission=4, group=groups)

        url = reverse_lazy("authenticate:user_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            self,
            model.user,
            profile=model.profile,
            permissions=[
                model.permission[3],
                model.permission[2],
                model.permission[1],
                model.permission[0],
            ],
            data={
                "settings": {
                    "lang": "en",
                    "main_currency": None,
                }
            },
        )

        self.assertEqual(json, expected)
