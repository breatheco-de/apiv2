"""
Test /academy
"""

import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase
from breathecode.admissions.models import Academy


def get_serializer(academy, country, city, data={}):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
        "street_address": academy.street_address,
        "country": country.code,
        "city": city.id,
        "is_hidden_on_prework": academy.is_hidden_on_prework,
        **data,
    }


class academyTestSuite(AdmissionsTestCase):
    """Test /academy"""

    def test_without_auth_should_be_ok(self):
        """Test /academy without auth"""
        url = reverse_lazy("admissions:academy")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_without_data(self):
        """Test /academy without auth"""
        url = reverse_lazy("admissions:academy")
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [])

    def test_with_data(self):
        """Test /academy without auth"""
        model = self.bc.database.create(authenticate=True, academy=True)
        url = reverse_lazy("admissions:academy")
        model_dict = self.remove_dinamics_fields(model.academy.__dict__)

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.academy, model.country, model.city)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                self.bc.format.to_dict(model.academy),
            ],
        )

    def test_status_in_querystring__status_not_found(self):
        """Test /academy without auth"""
        model = self.generate_models(authenticate=True, academy=True)
        url = reverse_lazy("admissions:academy") + "?status=asdsad"

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                self.bc.format.to_dict(model.academy),
            ],
        )

    def test_status_in_querystring__status_found(self):
        """Test /academy without auth"""
        statuses = ["INACTIVE", "ACTIVE", "DELETED"]
        cases = [(x, x, random.choice([y for y in statuses if x != y])) for x in statuses] + [
            (x, x.lower(), random.choice([y for y in statuses if x != y])) for x in statuses
        ]
        model = self.generate_models(authenticate=True, academy=3)

        for current, query, bad_status in cases:
            model.academy[0].status = current
            model.academy[0].save()

            model.academy[1].status = current
            model.academy[1].save()

            model.academy[2].status = bad_status
            model.academy[2].save()

            url = reverse_lazy("admissions:academy") + f"?status={query}"

            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(model.academy[0], model.country, model.city),
                get_serializer(model.academy[1], model.country, model.city),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("admissions.Academy"),
                [
                    {
                        **self.bc.format.to_dict(model.academy[0]),
                        "status": current,
                    },
                    {
                        **self.bc.format.to_dict(model.academy[1]),
                        "status": current,
                    },
                    {
                        **self.bc.format.to_dict(model.academy[2]),
                        "status": bad_status,
                    },
                ],
            )

    def test_post_without_auth(self):
        """Test POST /academy without auth"""
        url = reverse_lazy("admissions:academy")
        data = {
            "slug": "test-academy",
            "name": "Test Academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": 1,
            "country": 1,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [])

    def test_post_without_permission(self):
        """Test POST /academy without manage_organizations permission"""
        model = self.bc.database.create(user=True, city=True, country=True)
        self.client.force_authenticate(user=model.user)
        
        url = reverse_lazy("admissions:academy")
        data = {
            "slug": "test-academy",
            "name": "Test Academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": model.city.id,
            "country": model.country.code,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [])

    def test_post_with_permission_missing_required_fields(self):
        """Test POST /academy with permission but missing required fields"""
        permission = {"codename": "manage_organizations"}
        model = self.bc.database.create(user=True, permission=permission)
        model.user.user_permissions.add(model.permission)
        self.client.force_authenticate(user=model.user)

        url = reverse_lazy("admissions:academy")
        data = {"slug": "test-academy"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())
        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [])

    def test_post_with_permission_success(self):
        """Test POST /academy with permission and valid data"""
        permission = {"codename": "manage_organizations"}
        model = self.bc.database.create(user=True, permission=permission, city=True, country=True)
        model.user.user_permissions.add(model.permission)
        self.client.force_authenticate(user=model.user)

        url = reverse_lazy("admissions:academy")
        data = {
            "slug": "test-academy",
            "name": "Test Academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": model.city.id,
            "country": model.country.code,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        json = response.json()
        self.assertEqual(json["slug"], "test-academy")
        self.assertEqual(json["name"], "Test Academy")
        
        # Verify academy was created in database
        academies = self.bc.database.list_of("admissions.Academy")
        self.assertEqual(len(academies), 1)
        self.assertEqual(academies[0]["slug"], "test-academy")
        self.assertEqual(academies[0]["name"], "Test Academy")

    def test_post_with_duplicate_slug(self):
        """Test POST /academy with duplicate slug"""
        permission = {"codename": "manage_organizations"}
        model = self.bc.database.create(
            user=True, 
            permission=permission, 
            academy={"slug": "existing-academy"},
            city=True,
            country=True
        )
        model.user.user_permissions.add(model.permission)
        self.client.force_authenticate(user=model.user)

        url = reverse_lazy("admissions:academy")
        data = {
            "slug": "existing-academy",
            "name": "New Academy",
            "logo_url": "https://example.com/logo.png",
            "street_address": "123 Test St",
            "city": model.city.id,
            "country": model.country.code,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify only the original academy exists
        academies = self.bc.database.list_of("admissions.Academy")
        self.assertEqual(len(academies), 1)
        self.assertEqual(academies[0]["slug"], "existing-academy")
