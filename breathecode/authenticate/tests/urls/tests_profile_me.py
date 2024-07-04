"""
Test cases for /user
"""

import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


def get_serializer(profile, user):
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
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "username": user.username,
        },
    }


def post_serializer(user, data={}):
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
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "username": user.username,
        },
        **data,
    }


def put_serializer(profile, user, data={}):
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
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "username": user.username,
        },
        **data,
    }


def profile_fields(data={}):
    return {
        "avatar_url": None,
        "bio": None,
        "blog": None,
        "github_username": None,
        "id": 0,
        "linkedin_url": None,
        "phone": "",
        "portfolio_url": None,
        "show_tutorial": True,
        "twitter_username": None,
        "user_id": 0,
        **data,
    }


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        """Test /user/me without auth"""
        url = reverse_lazy("authenticate:profile_me")
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "Authentication credentials were not provided.",
            "status_code": status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET without permission
    """

    def test__get__without_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "without-permission", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET with zero Profile
    """

    def test__get__without_profile(self):
        """Test /user/me"""

        permission = {"codename": "get_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "profile-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.Profile"), [])

    """
    🔽🔽🔽 GET with one Profile
    """

    def test__get__with_profile(self):
        """Test /user/me"""

        permission = {"codename": "get_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission, profile=1)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(model.profile, model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                self.bc.format.to_dict(model.profile),
            ],
        )

    """
    🔽🔽🔽 POST without permission
    """

    def test__post__without_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "without-permission", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 POST without body
    """

    def test__post__without_body(self):
        """Test /user/me"""

        permission = {"codename": "create_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.post(url)

        json = response.json()
        expected = post_serializer(model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_fields(
                    {
                        "id": 1,
                        "user_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 POST passing the arguments
    """

    def test__post__passing_all_the_fields(self):
        """Test /user/me"""

        permission = {"codename": "create_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission)

        url = reverse_lazy("authenticate:profile_me")
        phone = f"+{random.randint(100000000, 999999999)}"
        data = {
            "avatar_url": self.bc.fake.url(),
            "bio": self.bc.fake.text(),
            "phone": phone,
            "show_tutorial": bool(random.getrandbits(1)),
            "twitter_username": self.bc.fake.name().replace(" ", "-"),
            "github_username": self.bc.fake.name().replace(" ", "-"),
            "portfolio_url": self.bc.fake.url(),
            "linkedin_url": self.bc.fake.url(),
            "blog": self.bc.fake.text()[:150].strip(),
        }

        response = self.client.post(url, data)

        json = response.json()
        expected = post_serializer(model.user, data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_fields(
                    {
                        "id": 1,
                        "user_id": 1,
                        **data,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 PUT without permission
    """

    def test__put__without_permission(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "without-permission", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT with zero Profile
    """

    def test__put__not_found(self):
        """Test /user/me"""

        permission = {"codename": "update_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "profile-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.Profile"), [])

    """
    🔽🔽🔽 PUT with one Profile
    """

    def test__put__with_one_profile__without_body(self):
        """Test /user/me"""

        permission = {"codename": "update_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission, profile=1)

        url = reverse_lazy("authenticate:profile_me")
        response = self.client.put(url)

        json = response.json()
        expected = put_serializer(model.profile, model.user)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                profile_fields(
                    {
                        "id": 1,
                        "user_id": 1,
                    }
                ),
            ],
        )

    """
    🔽🔽🔽 PUT with one Profile passing all the fields
    """

    def test__put__with_one_profile__passing_all_the_fields(self):
        """Test /user/me"""

        permission = {"codename": "update_my_profile"}
        model = self.generate_models(authenticate=True, permission=permission, profile=1)

        url = reverse_lazy("authenticate:profile_me")
        phone = f"+{random.randint(100000000, 999999999)}"
        data = {
            "avatar_url": self.bc.fake.url(),
            "bio": self.bc.fake.text(),
            "phone": phone,
            "show_tutorial": bool(random.getrandbits(1)),
            "twitter_username": self.bc.fake.name().replace(" ", "-"),
            "github_username": self.bc.fake.name().replace(" ", "-"),
            "portfolio_url": self.bc.fake.url(),
            "linkedin_url": self.bc.fake.url(),
            "blog": self.bc.fake.text()[:150].strip(),
        }
        response = self.client.put(url, data)

        json = response.json()
        expected = put_serializer(model.profile, model.user, data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                {
                    **self.bc.format.to_dict(model.profile),
                    **profile_fields(
                        {
                            "id": 1,
                            "user_id": 1,
                            **data,
                        }
                    ),
                }
            ],
        )
