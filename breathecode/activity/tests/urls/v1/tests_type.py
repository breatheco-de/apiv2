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
    def test_type__without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("activity:type")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type__wrong_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        url = reverse_lazy("activity:type")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("activity:type")
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
    🔽🔽🔽 Get
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_type(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True, profile_academy=True, capability="read_activity", role="potato")

        url = reverse_lazy("activity:type")
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "description": "Every time it logs in",
                "slug": "breathecode_login",
            },
            {
                "description": "First day using breathecode",
                "slug": "online_platform_registration",
            },
            {
                "description": "Attendy on an eventbrite event",
                "slug": "public_event_attendance",
            },
            {
                "description": "When the student attent to class",
                "slug": "classroom_attendance",
            },
            {
                "description": "When the student miss class",
                "slug": "classroom_unattendance",
            },
            {
                "description": "When a lessons is opened on the platform",
                "slug": "lesson_opened",
            },
            {
                "description": ("When the office raspberry pi detects the student"),
                "slug": "office_attendance",
            },
            {
                "description": "When a nps survey is answered by the student",
                "slug": "nps_survey_answered",
            },
            {
                "description": "When student successfully tests exercise",
                "slug": "exercise_success",
            },
            {"description": "When student successfully joins breathecode", "slug": "registration"},
            {
                "description": "Student cohort changes like: starts, drop, postpone, etc",
                "slug": "educational_status_change",
            },
            {
                "description": "Notes that can be added by teachers, TA's or anyone involved "
                "in the student education",
                "slug": "educational_note",
            },
            {
                "description": "Notes related to the student career",
                "slug": "career_note",
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
