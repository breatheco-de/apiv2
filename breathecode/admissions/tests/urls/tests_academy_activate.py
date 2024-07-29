"""
Test /academy
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class AcademyActivateTestSuite(AdmissionsTestCase):
    """Test /academy/activate"""

    def test_academy_without_auth(self):
        """Test /academy/activate without auth"""
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_without_academy_id(self):
        """Test /academy/activate without academy id in header"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_without_capability(self):
        """Test /academy/activate without capability"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
        )
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: academy_activate for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_when_academy_deleted(self):
        """Test /academy/activate with academy status deleted"""
        self.headers(academy=1)
        academy_kwargs = {"status": "DELETED"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="academy_activate",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {"detail": "This academy is deleted", "status_code": 403}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [self.bc.format.to_dict(model.academy)])

    def test_academy_when_academy_inactive(self):
        """Test /academy/activate with capability"""
        self.headers(academy=1)
        academy_kwargs = {"status": "INACTIVE"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="academy_activate",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "id": model.academy.id,
            "slug": model.academy.slug,
            "name": model.academy.name,
            "status": "ACTIVE",
            "country": {"code": model.academy.country.code, "name": model.academy.country.name},
            "city": {"name": model.academy.city.name},
            "logo_url": model.academy.logo_url,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [{**self.bc.format.to_dict(model.academy), "status": "ACTIVE"}],
        )

    def test_academy_when_academy_active(self):
        """Test /academy/activate with capability"""
        self.headers(academy=1)
        academy_kwargs = {"status": "ACTIVE"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="academy_activate",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_activate")
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            "id": model.academy.id,
            "slug": model.academy.slug,
            "name": model.academy.name,
            "status": "ACTIVE",
            "country": {"code": model.academy.country.code, "name": model.academy.country.name},
            "city": {"name": model.academy.city.name},
            "logo_url": model.academy.logo_url,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [{**self.bc.format.to_dict(model.academy), "status": "ACTIVE"}],
        )
