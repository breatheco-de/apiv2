"""
Test /certificate
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    def test_syllabus_id_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_id_without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
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

    def test_syllabus_id_without_data(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        model = self.generate_models(authenticate=True, profile_academy=True, capability="read_syllabus", role="potato")
        response = self.client.get(url)
        json = response.json()
        expected = {"status_code": 404, "detail": "syllabus-not-found"}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_syllabus_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {"slug": "they-killed-kenny"}
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_syllabus",
            role="potato",
            syllabus_version=True,
            syllabus=True,
            syllabus_kwargs=syllabus_kwargs,
        )
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug", kwargs={"academy_id": 1, "syllabus_slug": "they-killed-kenny"}
        )
        response = self.client.get(url)
        json = response.json()
        expected = {
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
            "main_technologies": None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test_syllabus_id__put__without_capabilities(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_syllabus " "for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus_id__put__setting_slug_as_empty(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        data = {"slug": ""}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "empty-slug", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus_id__put__setting_name_as_empty(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        data = {"name": ""}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "empty-name", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus_id__put__not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_syllabus", role="potato")
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug",
            kwargs={
                "academy_id": 1,
                "syllabus_slug": "they_killed_kenny",
            },
        )
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus_id__put__not_founds2(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus_schedule=True,
            syllabus_schedule_time_slot=True,
        )
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug", kwargs={"academy_id": 1, "syllabus_slug": "they-killed-kenny"}
        )
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_dict(), [])

    def test_syllabus_id__put(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {"slug": "they-killed-kenny"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus=True,
            syllabus_schedule=True,
            syllabus_schedule_time_slot=True,
            syllabus_kwargs=syllabus_kwargs,
        )
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug", kwargs={"academy_id": 1, "syllabus_slug": "they-killed-kenny"}
        )
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "slug": model.syllabus.slug,
            "name": model.syllabus.name,
            "academy_owner": model.syllabus.academy_owner.id,
            "duration_in_days": model.syllabus.duration_in_days,
            "duration_in_hours": model.syllabus.duration_in_hours,
            "week_hours": model.syllabus.week_hours,
            "github_url": model.syllabus.github_url,
            "id": model.syllabus.id,
            "logo": model.syllabus.logo,
            "private": model.syllabus.private,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test_syllabus_id__put__change_values(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_kwargs = {"slug": "they-killed-kenny"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            syllabus=True,
            syllabus_schedule=True,
            syllabus_schedule_time_slot=True,
            syllabus_kwargs=syllabus_kwargs,
        )
        url = reverse_lazy(
            "admissions:academy_id_syllabus_slug", kwargs={"academy_id": 1, "syllabus_slug": "they-killed-kenny"}
        )
        data = {
            "duration_in_days": 9,
            "duration_in_hours": 99,
            "week_hours": 999,
            "github_url": "https://tierragamer.com/wp-content/uploads/2020/08/naruto-cosplay-konan.jpg",
            "logo": "a",
            "private": not model.syllabus.private,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "academy_owner": model.syllabus.academy_owner.id,
            "id": model.syllabus.id,
            "slug": model.syllabus.slug,
            "name": model.syllabus.name,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus"),
                    **data,
                }
            ],
        )
