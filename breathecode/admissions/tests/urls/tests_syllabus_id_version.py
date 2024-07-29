"""
Test /certificate
"""

import random
from unittest.mock import patch, MagicMock
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status

from django.utils import timezone
from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


def generate_syllabus_json(lesson_slug, quiz_slug=None, reply_slug=None, project_slug=None, assignment_slug=None):

    if quiz_slug == None:
        quiz_slug = lesson_slug

    if reply_slug == None:
        reply_slug = quiz_slug

    if project_slug == None:
        project_slug = reply_slug

    if assignment_slug == None:
        assignment_slug = project_slug

    n = random.randint(1, 10)
    return {
        "days": [
            {
                "lessons": [
                    {
                        "slug": lesson_slug,
                    }
                ],
                "quizzes": [
                    {
                        "slug": quiz_slug,
                    }
                ],
                "replits": [
                    {
                        "slug": reply_slug,
                    }
                ],
                "projects": [
                    {
                        "slug": project_slug,
                    }
                ],
                "assignments": [
                    {
                        "slug": assignment_slug,
                    }
                ],
            }
            for _ in range(n)
        ]
    }


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_syllabus_id_version_without_auth(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:syllabus_id_version", kwargs={"syllabus_id": "1"})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_id_version_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:syllabus_id_version", kwargs={"syllabus_id": "1"})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            "status_code": 403,
            "detail": "You (user: 1) don't have this capability: read_syllabus " "for academy 1",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_id_version_without_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, syllabus_schedule=True, profile_academy=True, capability="read_syllabus", role="potato"
        )
        url = reverse_lazy("admissions:syllabus_id_version", kwargs={"syllabus_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [])
        self.assertEqual(self.all_syllabus_version_dict(), [])

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_syllabus_id_version(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_syllabus",
            role="potato",
            syllabus=True,
            syllabus_version=True,
        )
        url = reverse_lazy(
            "admissions:syllabus_id_version",
            kwargs={
                "syllabus_id": 1,
            },
        )
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "json": model["syllabus_version"].json,
                "created_at": datetime_to_iso_format(model["syllabus_version"].created_at),
                "updated_at": datetime_to_iso_format(model["syllabus_version"].updated_at),
                "name": model["syllabus"].name,
                "slug": model["syllabus"].slug,
                "syllabus": 1,
                "academy_owner": {
                    "id": model["syllabus"].academy_owner.id,
                    "name": model["syllabus"].academy_owner.name,
                    "slug": model["syllabus"].academy_owner.slug,
                    "white_labeled": model["syllabus"].academy_owner.white_labeled,
                    "icon_url": model["syllabus"].academy_owner.icon_url,
                    "available_as_saas": model["syllabus"].academy_owner.available_as_saas,
                },
                "version": model["syllabus_version"].version,
                "duration_in_days": model.syllabus.duration_in_days,
                "duration_in_hours": model.syllabus.duration_in_hours,
                "github_url": model.syllabus.github_url,
                "logo": model.syllabus.logo,
                "private": model.syllabus.private,
                "main_technologies": None,
                "week_hours": model.syllabus.week_hours,
                "change_log_details": None,
                "status": "PUBLISHED",
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_version_dict(), [{**self.model_to_dict(model, "syllabus_version")}])

    def test_syllabus_id_version__post__bad_syllabus_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy(
            "admissions:syllabus_id_version",
            kwargs={
                "syllabus_id": 9999,
            },
        )
        data = {}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_version_dict(), [])

    def test_syllabus_id_version__post__without_json_field(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy(
            "admissions:syllabus_id_version",
            kwargs={
                "syllabus_id": 1,
            },
        )
        data = {}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"json": ["This field is required."]}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_version_dict(), [])

    def test_syllabus_id_version__post(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        slug = self.bc.fake.slug()
        asset_alias = {"slug": slug}
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            asset_alias=asset_alias,
            syllabus=True,
        )
        url = reverse_lazy(
            "admissions:syllabus_id_version",
            kwargs={
                "syllabus_id": 1,
            },
        )
        data = {"json": generate_syllabus_json(slug)}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "syllabus": 1,
            "version": 1,
            "change_log_details": None,
            "status": "PUBLISHED",
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_version_dict(),
            [
                {
                    "id": 1,
                    "integrity_check_at": None,
                    "integrity_report": None,
                    "integrity_status": "PENDING",
                    "json": {},
                    "change_log_details": None,
                    "status": "PUBLISHED",
                    "syllabus_id": 1,
                    "version": 1,
                    **data,
                }
            ],
        )

    def test_syllabus_id_version__post__autoincrement_version(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        slug = self.bc.fake.slug()
        asset_alias = {"slug": slug}
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus=True,
            asset_alias=asset_alias,
            syllabus_version=True,
        )
        url = reverse_lazy(
            "admissions:syllabus_id_version",
            kwargs={
                "syllabus_id": 1,
            },
        )
        data = {"json": generate_syllabus_json(slug)}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "syllabus": 1,
            "change_log_details": None,
            "status": "PUBLISHED",
            "version": model.syllabus_version.version + 1,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_version_dict(),
            [
                {**self.model_to_dict(model, "syllabus_version")},
                {
                    "id": 2,
                    "integrity_check_at": None,
                    "integrity_report": None,
                    "integrity_status": "PENDING",
                    "change_log_details": None,
                    "status": "PUBLISHED",
                    "json": {},
                    "syllabus_id": 1,
                    "version": model.syllabus_version.version + 1,
                    **data,
                },
            ],
        )
