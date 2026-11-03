"""
Test cases for /user
"""

import os
import urllib

from django.urls.base import reverse_lazy
from rest_framework import status

from ...mixins import AuthTestCase

# from ..mocks import GithubRequestsMock


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test_github_without_url(self):
        """Test /github without auth"""
        url = reverse_lazy("authenticate:github")
        response = self.client.get(url)

        data = response.data

        expected = {"detail": "no-callback-url", "status_code": 400}

        self.assertEqual(data, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_github(self):
        """Test /github"""
        original_url_callback = "https://4geeks.com"
        url = reverse_lazy("authenticate:github")
        params = {"url": "https://4geeks.com"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")
        params = {
            "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
            "redirect_uri": os.getenv("GITHUB_REDIRECT_URL", "") + "?url=" + original_url_callback,
            "scope": "user",
        }

        redirect = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect)

    def test_github__with_url_not_allowed(self):
        """Test /github with a callback outside the allowlist"""
        url = reverse_lazy("authenticate:github")
        for callback in ["https://evil.com", "https://4geeks.com.evil.com/callback"]:
            response = self.client.get(f"{url}?{urllib.parse.urlencode({'url': callback})}")

            self.assertEqual(response.data, {"detail": "invalid-redirect-url", "status_code": 400})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
