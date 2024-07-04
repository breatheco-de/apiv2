"""
Test /certificate
"""

from random import choice, randint
import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_academy_schedule_id__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_academy_schedule_id__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        self.generate_models(authenticate=True)
        response = self.client.put(url)
        json = response.json()
        expected = {
            "status_code": 403,
            "detail": "You (user: 1) don't have this capability: crud_certificate for academy 1",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_academy_schedule_id__not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        response = self.client.put(url)
        json = response.json()
        expected = {
            "detail": "specialty-mode-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_academy_schedule_id__schedule_of_other_academy(self):
        """Test /certificate without auth"""
        self.headers(academy=1)

        syllabus_schedule = {"academy_id": 2}
        model = self.generate_models(
            authenticate=1,
            syllabus_schedule=syllabus_schedule,
            academy=2,
            profile_academy=1,
            capability="crud_certificate",
            role="potato",
        )

        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        data = {
            "slug": "they-killed-kenny",
            "name": "They killed kenny",
            "description": "Oh my god!",
            "syllabus": 2,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "syllabus-schedule-of-other-academy", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                }
            ],
        )

    def test_academy_schedule_id__bad_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=1,
            syllabus_schedule=1,
            academy=1,
            profile_academy=1,
            capability="crud_certificate",
            role="potato",
        )
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        data = {
            "slug": "they-killed-kenny",
            "name": "They killed kenny",
            "description": "Oh my god!",
            "syllabus": 2,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "syllabus-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                }
            ],
        )

    def test_academy_schedule_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
        )
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        data = {"name": "They killed kenny", "description": "Oh my god!"}
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "created_at": self.datetime_to_iso(model.syllabus_schedule.created_at),
            "id": model.syllabus_schedule.id,
            "schedule_type": model.syllabus_schedule.schedule_type,
            "syllabus": model.syllabus_schedule.syllabus,
            "academy": model.syllabus_schedule.academy.id,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                    **data,
                }
            ],
        )

    def test_academy_schedule_id__passing_all_status__in_lowercase(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
        )
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        schedule_type = random.choice(["PART-TIME", "FULL-TIME"])
        data = {
            "name": "They killed kenny",
            "description": "Oh my god!",
            "schedule_type": schedule_type.lower(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "created_at": self.datetime_to_iso(model.syllabus_schedule.created_at),
            "id": model.syllabus_schedule.id,
            "schedule_type": model.syllabus_schedule.schedule_type,
            "syllabus": model.syllabus_schedule.syllabus,
            "academy": model.syllabus_schedule.academy.id,
            **data,
            "schedule_type": schedule_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                    **data,
                    "schedule_type": schedule_type,
                }
            ],
        )

    def test_academy_schedule_id__passing_all_status__in_uppercase(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
        )
        url = reverse_lazy("admissions:academy_schedule_id", kwargs={"certificate_id": 1})
        schedule_type = random.choice(["PART-TIME", "FULL-TIME"])
        data = {
            "name": "They killed kenny",
            "description": "Oh my god!",
            "schedule_type": schedule_type,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "created_at": self.datetime_to_iso(model.syllabus_schedule.created_at),
            "id": model.syllabus_schedule.id,
            "schedule_type": model.syllabus_schedule.schedule_type,
            "syllabus": model.syllabus_schedule.syllabus,
            "academy": model.syllabus_schedule.academy.id,
            **data,
            "schedule_type": schedule_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    **self.model_to_dict(model, "syllabus_schedule"),
                    **data,
                    "schedule_type": schedule_type,
                }
            ],
        )
