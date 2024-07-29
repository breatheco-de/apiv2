"""
Test cases for /user
"""

import urllib
import os
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase

# from ..mocks import GithubRequestsMock


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test_github_id_without_url(self):
        """Test /github without auth"""
        url = reverse_lazy("authenticate:github_token", kwargs={"token": None})
        url = urllib.parse.quote(url.encode("utf-8"))
        response = self.client.get(url)

        data = response.data

        expected = {"detail": "no-callback-url", "status_code": 400}

        self.assertEqual(2, len(data))
        self.assertEqual(data, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_github_id_with_args_no_invalid_token(self):
        """Test /github"""
        url = reverse_lazy("authenticate:github_token", kwargs={"token": "asdasd"})
        url = urllib.parse.quote(url.encode("utf-8"))
        params = {"url": "https://google.co.ve"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")
        json = response.json()
        expected = {"detail": "invalid-token", "status_code": 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_github_with_auth(self):
        """Test /github"""
        original_url_callback = "https://google.co.ve"
        model = self.generate_models(authenticate=True, token=True)
        token = self.get_token(1)
        url = reverse_lazy(
            "authenticate:github_token",
            kwargs={
                "token": token,
            },
        )
        url = urllib.parse.quote(url.encode("utf-8"))
        params = {"url": "https://google.co.ve"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")
        params = {
            "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
            "redirect_uri": os.getenv("GITHUB_REDIRECT_URL", "") + f"?url={original_url_callback}&user={token}",
            "scope": "user repo read:org",
        }

        redirect = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}+admin%3Aorg"
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect)
