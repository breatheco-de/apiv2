"""
Test /certificate
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_syllabus_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            "status_code": 403,
            "detail": "You (user: 1) don't have this capability: read_syllabus for academy 1",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_without_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, syllabus_schedule=True, profile_academy=True, capability="read_syllabus", role="potato"
        )
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_syllabus",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "main_technologies": None,
                "slug": model.syllabus.slug,
                "name": model.syllabus.name,
                "academy_owner": {
                    "id": model.syllabus.academy_owner.id,
                    "name": model.syllabus.academy_owner.name,
                    "slug": model.syllabus.academy_owner.slug,
                    "white_labeled": model.syllabus.academy_owner.white_labeled,
                    "icon_url": model.syllabus.academy_owner.icon_url,
                    "available_as_saas": model.syllabus.academy_owner.available_as_saas,
                },
                "duration_in_days": model.syllabus.duration_in_days,
                "duration_in_hours": model.syllabus.duration_in_hours,
                "week_hours": model.syllabus.week_hours,
                "github_url": model.syllabus.github_url,
                "id": model.syllabus.id,
                "logo": model.syllabus.logo,
                "private": model.syllabus.private,
                "created_at": self.datetime_to_iso(model.syllabus.created_at),
                "updated_at": self.datetime_to_iso(model.syllabus.updated_at),
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test_syllabus_post_without_capabilities(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_syllabus " "for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus__post__missing_slug_in_request(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        data = {}
        response = self.client.post(url, data, format="json")
        json = response.json()

        expected = {"detail": "missing-slug", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus__post__missing_name_in_request(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        data = {"slug": "they-killed-kenny"}
        response = self.client.post(url, data, format="json")
        json = response.json()

        expected = {"detail": "missing-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus__post(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy("admissions:academy_id_syllabus", kwargs={"academy_id": 1})
        data = {
            "slug": "they-killed-kenny",
            "name": "They killed kenny",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()

        expected = {
            "academy_owner": 1,
            "duration_in_days": None,
            "duration_in_hours": None,
            "github_url": None,
            "id": 1,
            "logo": None,
            "private": False,
            "week_hours": None,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_dict(),
            [
                {
                    "main_technologies": None,
                    "academy_owner_id": 1,
                    "duration_in_days": None,
                    "duration_in_hours": None,
                    "github_url": None,
                    "id": 1,
                    "is_documentation": False,
                    "logo": None,
                    "private": False,
                    "week_hours": None,
                    **data,
                }
            ],
        )
