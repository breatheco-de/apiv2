"""
Test /answer
"""

from unittest.mock import patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)

from ...mixins import MediaTestCase


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Auth
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type_slug__without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("activity:type_slug", kwargs={"activity_slug": "they-killed-kenny"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type_slug__wrong_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        url = reverse_lazy("activity:type_slug", kwargs={"activity_slug": "they-killed-kenny"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type_slug__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("activity:type_slug", kwargs={"activity_slug": "they-killed-kenny"})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: read_activity for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Bad slug
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type_slug__without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:type_slug", kwargs={"activity_slug": "they-killed-kenny"})
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "activity-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Get
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type_slug(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:type_slug", kwargs={"activity_slug": "career_note"})
        response = self.client.get(url)
        json = response.json()
        expected = {
            "description": "Notes related to the student career",
            "slug": "career_note",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
