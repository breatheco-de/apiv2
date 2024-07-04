"""
Test cases for /user
"""

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase


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
