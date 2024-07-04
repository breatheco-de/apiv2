"""
Test cases for /user
"""

from unittest.mock import MagicMock

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase


def credentials_github_serializer(credentials_github):
    return {
        "avatar_url": credentials_github.avatar_url,
        "name": credentials_github.name,
        "username": credentials_github.username,
    }


def profile_serializer(credentials_github):
    return {
        "avatar_url": credentials_github.avatar_url,
    }


def get_serializer(user, credentials_github=None, profile=None, **data):
    return {
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "github": credentials_github_serializer(credentials_github) if credentials_github else None,
        "id": user.id,
        "last_name": user.last_name,
        "date_joined": user.date_joined,
        "profile": profile_serializer(profile) if profile else None,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    from linked_services.django.actions import reset_app_cache

    reset_app_cache()
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())
    yield


class AuthenticateTestSuite(AuthTestCase):

    # When: no auth
    # Then: return 401
    def test_no_auth(self):
        url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "no-authorization-header",
            "status_code": status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: Sign with an user
    # Then: return 200
    def test_sign_with_user__get_own_info(self):
        app = {"require_an_agreement": False, "slug": "rigobot"}
        credentials_githubs = [{"user_id": x + 1} for x in range(2)]
        profiles = [{"user_id": x + 1} for x in range(2)]
        model = self.bc.database.create(
            user=2,
            app=app,
            profile=profiles,
            credentials_github=credentials_githubs,
            first_party_credentials={
                "app": {
                    "rigobot": 1,
                },
            },
        )
        self.bc.request.sign_jwt_link(model.app, 1)

        url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            model.user[0],
            model.credentials_github[0],
            model.profile[0],
            date_joined=self.bc.datetime.to_iso_string(model.user[0].date_joined),
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("auth.User"), self.bc.format.to_dict(model.user))

    # When: Sign with an user
    # Then: return 200
    def test_sign_with_user__get_info_from_another(self):
        app = {"require_an_agreement": False, "slug": "rigobot"}
        credentials_githubs = [{"user_id": x + 1} for x in range(2)]
        profiles = [{"user_id": x + 1} for x in range(2)]
        model = self.bc.database.create(
            user=2,
            app=app,
            profile=profiles,
            credentials_github=credentials_githubs,
            first_party_credentials={
                "app": {
                    "rigobot": 1,
                },
            },
        )
        self.bc.request.sign_jwt_link(model.app, 1)

        url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": 2})
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "user-with-no-access",
            "silent": True,
            "silent_code": "user-with-no-access",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("auth.User"), self.bc.format.to_dict(model.user))

    # When: Sign without an user
    # Then: return 200
    def test_sign_without_user(self):
        app = {"require_an_agreement": False}
        credentials_githubs = [{"user_id": x + 1} for x in range(2)]
        profiles = [{"user_id": x + 1} for x in range(2)]
        model = self.bc.database.create(user=2, app=app, profile=profiles, credentials_github=credentials_githubs)
        self.bc.request.sign_jwt_link(model.app)

        for user in model.user:
            url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": user.id})
            response = self.client.get(url)

            json = response.json()
            expected = get_serializer(
                user,
                model.credentials_github[user.id - 1],
                model.profile[user.id - 1],
                date_joined=self.bc.datetime.to_iso_string(user.date_joined),
            )

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("auth.User"), self.bc.format.to_dict(model.user))

    # When: Sign user with no agreement
    # Then: return 200
    def test_user_with_no_agreement(self):
        app = {"require_an_agreement": False, "require_an_agreement": True}
        credentials_github = {"user_id": 1}
        profile = {"user_id": 1}
        model = self.bc.database.create(user=1, app=app, profile=profile, credentials_github=credentials_github)
        self.bc.request.sign_jwt_link(model.app)

        url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "user-not-found",
            "silent": True,
            "silent_code": "user-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])

    # When: Sign user with agreement
    # Then: return 200
    def test_user_with_agreement(self):
        app = {"require_an_agreement": False, "require_an_agreement": True}
        credentials_github = {"user_id": 1}
        profile = {"user_id": 1}
        model = self.bc.database.create(
            user=1, app=app, profile=profile, credentials_github=credentials_github, app_user_agreement=1
        )
        self.bc.request.sign_jwt_link(model.app)

        url = reverse_lazy("authenticate:app_user_id", kwargs={"user_id": 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(
            model.user,
            model.credentials_github,
            model.profile,
            date_joined=self.bc.datetime.to_iso_string(model.user.date_joined),
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
