"""
Test cases for GET /v1/auth/github/<user_id> (academy staff with read_student).
"""

from unittest.mock import patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.github import GithubAuthException

from ...mixins.new_auth_test_case import AuthTestCase


class GithubUserByIdTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Auth and Academy header
    """

    def test_get__without_auth(self):
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get__without_academy_header(self):
        model = self.generate_models(authenticate=True, role="staff", capability="read_student", profile_academy=True)
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 1})
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Missing academy_id", json.get("detail", ""))

    def test_get__without_capability(self):
        self.bc.request.set_headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_student for academy 1",
            "status_code": 403,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Student not in academy / No GitHub credentials
    """

    def test_get__student_not_in_academy(self):
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(
            authenticate=True, role="staff", capability="read_student", profile_academy=True
        )
        # user_id=2 has no profile_academy in this academy
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 2})
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "profile-academy-not-found", "status_code": 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get__student_in_academy__no_github_credentials(self):
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(
            authenticate=True, role="staff", capability="read_student", profile_academy=True
        )
        # Add user 2 as student in academy 1
        self.bc.database.create(
            user=2, profile_academy=1, academy=model["academy"], role="student"
        )
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 2})
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "not-found", "status_code": 404}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 GET found, returns credentials with scopes and valid
    """

    @patch("breathecode.authenticate.views.Github")
    def test_get__student_with_github__valid_token(self, mock_github_class):
        mock_github_class.return_value.get.return_value = {"login": "octocat"}
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(
            authenticate=True, role="staff", capability="read_student", profile_academy=True
        )
        credentials_github = {
            "username": "octocat",
            "avatar_url": "https://avatars.githubusercontent.com/u/1",
            "name": "The Octocat",
            "scopes": "admin:org delete_repo repo user user:email",
            "token": "gho_valid_token",
        }
        self.bc.database.create(
            user=2,
            profile_academy=1,
            academy=model["academy"],
            role="student",
            credentials_github=credentials_github,
        )
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 2})
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
    def test_get__student_with_github__invalid_token(self, mock_github_class):
        mock_github_class.return_value.get.side_effect = GithubAuthException("Invalid credentials")
        self.bc.request.set_headers(academy=1)
        model = self.generate_models(
            authenticate=True, role="staff", capability="read_student", profile_academy=True
        )
        credentials_github = {
            "username": "octocat",
            "scopes": "user:email",
            "token": "gho_expired",
        }
        self.bc.database.create(
            user=2,
            profile_academy=1,
            academy=model["academy"],
            role="student",
            credentials_github=credentials_github,
        )
        url = reverse_lazy("authenticate:github_user_by_id", kwargs={"user_id": 2})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "octocat")
        self.assertEqual(data["scopes"], "user:email")
        self.assertIs(data["valid"], False)
