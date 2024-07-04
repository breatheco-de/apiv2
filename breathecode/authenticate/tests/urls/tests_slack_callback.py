"""
Test cases for /user
"""

import base64
import urllib
from unittest import mock
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase, SlackTestCase
from ..mocks import SlackRequestsMock


class AuthenticateTestSuite(AuthTestCase, SlackTestCase):
    """Authentication test suite"""

    def test_slack_callback_with_error(self):
        """Test /slack/callback without auth"""
        url = reverse_lazy("authenticate:slack_callback")
        params = {"error": "Oh my god", "error_description": "They killed kenny"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        detail = str(data["detail"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(detail, "Slack: They killed kenny")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_slack_callback_without_callback(self):
        """Test /slack/callback without auth"""
        url = reverse_lazy("authenticate:slack_callback")
        response = self.client.get(url)

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No payload specified")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_with_bad_callback(self):
        """Test /slack/callback without auth"""
        url = reverse_lazy("authenticate:slack_callback")
        params = {"payload": "They killed kenny"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "Cannot decode payload in base64")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_without_url_in_payload(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        url = reverse_lazy("authenticate:slack_callback")

        query_string = "".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No url specified from the slack payload")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_without_user_in_payload(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        academy = 2

        query_string = f"a={academy}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No user id specified from the slack payload")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_without_a_in_payload(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        user = 1

        query_string = f"user={user}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No academy id specified from the slack payload")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_with_user_in_payload_but_not_exist(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        academy = 2
        user = 1

        query_string = f"user={user}&a={academy}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "Not exist academy with that id")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_with_a_in_payload_but_not_exist(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        academy = 1
        user = 2

        query_string = f"user={user}&a={academy}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "Not exist user with that id")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slack_callback_without_code(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        academy = 1
        user = 1

        query_string = f"user={user}&a={academy}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        data = response.data
        details = str(data["details"])
        status_code = data["status_code"]

        self.assertEqual(2, len(data))
        self.assertEqual(details, "No slack code specified")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("requests.post", SlackRequestsMock.apply_post_requests_mock())
    def test_slack_callback_without_code2(self):
        """Test /slack/callback without auth"""
        self.slack()
        self.get_academy()
        original_url_callback = self.url_callback
        url = reverse_lazy("authenticate:slack_callback")
        academy = 1
        user = 1

        query_string = f"user={user}&a={academy}&url={original_url_callback}".encode("utf-8")
        payload = str(base64.urlsafe_b64encode(query_string), "utf-8")
        params = {"payload": payload, "code": "haha"}
        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

        self.assertEqual(response.url, original_url_callback)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
