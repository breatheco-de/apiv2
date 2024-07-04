"""
Test /certificate
"""

from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_certificate_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:schedule_id", kwargs={"schedule_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:schedule_id", kwargs={"schedule_id": 1})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {"status_code": 404, "detail": "schedule-not-found"}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True, syllabus_schedule=True, syllabus=True)
        url = reverse_lazy("admissions:schedule_id", kwargs={"schedule_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "id": model["syllabus_schedule"].id,
                "name": model["syllabus_schedule"].name,
                "description": model["syllabus_schedule"].description,
                "syllabus": model["syllabus_schedule"].syllabus.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                }
            ],
        )
