"""
Test cases for /profile/<int:user_id>
"""

import pytz, datetime
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


def get_serializer(self, profile, data={}):
    return {
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "blog": profile.blog,
        "github_username": profile.github_username,
        "linkedin_url": profile.linkedin_url,
        "phone": profile.phone,
        "portfolio_url": profile.portfolio_url,
        "show_tutorial": profile.show_tutorial,
        "twitter_username": profile.twitter_username,
        "user": {
            "id": profile.user.id,
            "email": profile.user.email,
            "username": profile.user.username,
            "first_name": profile.user.first_name,
            "last_name": profile.user.last_name,
        },
        **data,
    }


def put_serializer(self, profile, data={}):
    return {
        "id": profile.id,
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "blog": profile.blog,
        "github_username": profile.github_username,
        "linkedin_url": profile.linkedin_url,
        "phone": profile.phone,
        "portfolio_url": profile.portfolio_url,
        "show_tutorial": profile.show_tutorial,
        "twitter_username": profile.twitter_username,
        "user": profile.user.id,
        **data,
    }


def profile_row(data={}):
    return {
        "avatar_url": None,
        "bio": None,
        "blog": None,
        "github_username": None,
        "linkedin_url": None,
        "phone": "",
        "portfolio_url": None,
        "show_tutorial": True,
        "twitter_username": None,
        **data,
    }


class ProfileTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_user_profile__without_auth(self):
        """Test /profile/id without auth"""
        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Authentication credentials were not provided.",
            "status_code": status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_profile__wrong_academy(self):
        """Test /profile/id with wrong academy"""
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_profile__wrong_user_id(self):
        """Test /profile/id"""
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True, capability="crud_event", role="role", profile_academy=1)

        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "profile-not-found",
            "status_code": status.HTTP_404_NOT_FOUND,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_profile(self):
        """Test /profile/id"""
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(
            authenticate=True, profile=1, capability="crud_event", role="role", profile_academy=1
        )

        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self, model.profile)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_user_profile__wrong_user_id(self):
        """Test put /profile/id"""
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True, capability="crud_event", role="role", profile_academy=1)

        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )
        response = self.client.put(url)

        json = response.json()
        expected = {
            "detail": "profile-not-found",
            "status_code": status.HTTP_404_NOT_FOUND,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_user_profile(self):
        """Test /profile/id"""
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(
            authenticate=True, profile=1, capability="crud_event", role="role", profile_academy=1
        )

        url = reverse_lazy(
            "authenticate:user_profile",
            kwargs={
                "user_id": 1,
            },
        )

        data = {
            "user": 1,
            "avatar_url": "https://google.com",
            "bio": "blablabla",
            "phone": "+1555555555",
            "show_tutorial": False,
            "twitter_username": "Kenny",
            "github_username": "Kenny",
            "portfolio_url": "Kenny",
            "linkedin_url": "Kenny",
            "blog": "Kenny",
        }
        response = self.client.put(url, data)

        json = response.json()
        expected = put_serializer(self, model.profile, data=data)

        bc_data = {**data, "user_id": 1, "id": 1}
        bc_data.pop("user", None)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_row(data={**bc_data}),
            ],
        )
