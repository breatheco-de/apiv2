"""
Test /academy/cohort
"""

import re
from datetime import datetime
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


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_user_post_without_authorization(self):
        """Test /academy/cohort without auth"""
        url = reverse_lazy("admissions:user")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_user_post_without_data(self):
        """Test /academy/cohort without auth"""
        model = self.generate_models(authenticate=True)
        model_dict = self.get_user_dict(1)
        url = reverse_lazy("admissions:user")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "id": model.user.id,
            "first_name": model.user.first_name,
            "last_name": model.user.last_name,
            "email": model.user.email,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_user(), 1)
        self.assertEqual(self.get_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_user_post(self):
        """Test /academy/cohort without auth"""
        model = self.generate_models(authenticate=True, user=True)
        model_dict = self.get_user_dict(1)
        url = reverse_lazy("admissions:user")
        data = {
            "first_name": "Socrates",
            "last_name": "Aristoteles",
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "id": model.user.id,
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "email": model.user.email,
        }

        model_dict.update(data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_user(), 1)
        self.assertEqual(self.get_user_dict(1), model_dict)
