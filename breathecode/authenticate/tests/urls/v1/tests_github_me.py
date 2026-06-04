"""
Test cases for /user
"""

from unittest.mock import patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.github import GithubAuthException

from ...mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_not_auth(self):
        url = reverse_lazy("authenticate:github_me")
        response = self.client.delete(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get__not_auth(self):
        url = reverse_lazy("authenticate:github_me")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 GET not found
    """

    def test__get__not_found(self):
        model = self.bc.database.create(user=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 GET found, returns credentials with scopes and valid
    """

    @patch("breathecode.authenticate.views.Github")
    def test__get__found(self, mock_github_class):
        mock_github_class.return_value.get.return_value = {"login": "octocat"}

        credentials_github = {
            "username": "octocat",
            "avatar_url": "https://avatars.githubusercontent.com/u/1",
            "name": "The Octocat",
            "scopes": "admin:org delete_repo repo user user:email",
            "token": "gho_valid_token",
        }
        model = self.bc.database.create(user=1, credentials_github=credentials_github)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "octocat")
        self.assertEqual(data["avatar_url"], "https://avatars.githubusercontent.com/u/1")
        self.assertEqual(data["name"], "The Octocat")
        self.assertEqual(data["scopes"], "admin:org delete_repo repo user user:email")
        self.assertIs(data["valid"], True)
        mock_github_class.return_value.get.assert_called_once_with("/user")

    @patch("breathecode.authenticate.views.Github")
    def test__get__found__token_invalid(self, mock_github_class):
        mock_github_class.return_value.get.side_effect = GithubAuthException("Invalid credentials")

        credentials_github = {
            "username": "octocat",
            "scopes": "user:email",
            "token": "gho_expired",
        }
        model = self.bc.database.create(user=1, credentials_github=credentials_github)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "octocat")
        self.assertEqual(data["scopes"], "user:email")
        self.assertIs(data["valid"], False)

    """
    🔽🔽🔽 DELETE not found
    """

    def test__delete__not_found(self):
        model = self.bc.database.create(user=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.delete(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.CredentialsGithub"), [])

    """
    🔽🔽🔽 DELETE not found, trying to delete a CredentialsGithub from another User
    """

    def test__delete__not_found__trying_to_delete_credentials_of_other_user(self):
        credentials_github = {"user_id": 2}
        model = self.bc.database.create(user=2, credentials_github=credentials_github)

        self.bc.request.authenticate(model.user[0])
        url = reverse_lazy("authenticate:github_me")
        response = self.client.delete(url)

        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.bc.database.list_of("authenticate.CredentialsGithub"),
            [
                self.bc.format.to_dict(model.credentials_github),
            ],
        )

    """
    🔽🔽🔽 DELETE found, it's deleted
    """

    def test__delete__found(self):
        model = self.bc.database.create(user=1, credentials_github=1)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of("authenticate.CredentialsGithub"), [])

    """
    🔽🔽🔽 DELETE found, it's deleted, with Profile, the image keep
    """

    def test__delete__found__with_profile__keep_the_image(self):
        profile = {"avatar_url": self.bc.fake.url()}
        model = self.bc.database.create(user=1, credentials_github=1, profile=profile)

        self.client.force_authenticate(model.user)
        url = reverse_lazy("authenticate:github_me")
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of("authenticate.CredentialsGithub"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                self.bc.format.to_dict(model.profile),
            ],
        )
