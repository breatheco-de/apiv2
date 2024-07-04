"""
Test cases for /user
"""

import base64
import os
import urllib

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test_slack_without_url(self):
        """Test /slack without auth"""
        url = reverse_lazy("authenticate:slack")
        response = self.client.get(url)

        data = response.data
        details = data["details"]
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No callback URL specified")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_without_user(self):
        """Test /slack without auth"""
        original_url_callback = "https://google.co.ve"
        url = reverse_lazy("authenticate:slack")
        params = {
            "url": base64.b64encode(original_url_callback.encode("utf-8")),
        }
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = data["details"]
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No user specified on the URL")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_without_a(self):
        """Test /slack without auth"""
        original_url_callback = "https://google.co.ve"
        url = reverse_lazy("authenticate:slack")
        user = "1234567890"
        params = {"url": base64.b64encode(original_url_callback.encode("utf-8")), "user": user}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = data["details"]
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No academy specified on the URL")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack(self):
        """Test /slack"""
        original_url_callback = "https://google.co.ve"
        url = reverse_lazy("authenticate:slack")
        academy = "Team 7"
        user = "1234567890"
        params = {"url": base64.b64encode(original_url_callback.encode("utf-8")), "user": user, "a": academy}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        query_string = f"a={academy}&url={original_url_callback}&user={user}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        scopes = (
            "app_mentions:read",
            "channels:history",
            "channels:join",
            "channels:read",
            "chat:write",
            "chat:write.customize",
            "commands",
            "files:read",
            "files:write",
            "groups:history",
            "groups:read",
            "groups:write",
            "incoming-webhook",
            "team:read",
            "users:read",
            "users:read.email",
            "users.profile:read",
            "users:read",
        )
        params = {
            "client_id": os.getenv("SLACK_CLIENT_ID", ""),
            "redirect_uri": os.getenv("SLACK_REDIRECT_URL", "") + "?payload=" + payload,
            "scope": ",".join(scopes),
        }

        redirect = "https://slack.com/oauth/v2/authorize?"
        for key in params:
            redirect += f"{key}={params[key]}&"

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, redirect)
