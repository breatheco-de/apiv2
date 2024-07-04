"""
Test /academy
"""

import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


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
