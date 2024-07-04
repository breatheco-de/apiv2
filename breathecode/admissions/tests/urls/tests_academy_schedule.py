"""
Test /certificate
"""

from random import choice, randint
import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


def get_serializer(syllabus_schedule):
    return {
        "id": syllabus_schedule.id,
        "name": syllabus_schedule.name,
        "description": syllabus_schedule.description,
        "syllabus": syllabus_schedule.syllabus.id,
    }


class CertificateTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_schedule")
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            "status_code": 403,
            "detail": "You (user: 1) don't have this capability: read_certificate for academy 1",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test__with_schedule_of_other_academy(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        syllabus_schedule = {"academy_id": 2}
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=syllabus_schedule,
            academy=2,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
        )
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_academy_schedule(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.syllabus_schedule)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    """
    🔽🔽🔽 Syllabus id in querystring
    """

    def test__syllabus_id_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_schedule") + "?syllabus_id=9999"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test__syllabus_id_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_schedule") + "?syllabus_id=1"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.syllabus_schedule)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    """
    🔽🔽🔽 schedule_type in querystring
    """

    def test__schedule_type_in_querystring__not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_schedule") + "?schedule_type=asdasdasd"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test__schedule_type_in_querystring__found(self):
        """Test /certificate without auth"""
        statuses = ["PARTIME", "FULLTIME"]
        cases = [(x, x, random.choice([y for y in statuses if x != y])) for x in statuses] + [
            (x, x.lower(), random.choice([y for y in statuses if x != y])) for x in statuses
        ]
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=3,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )

        for current, query, bad_status in cases:
            model.syllabus_schedule[0].schedule_type = current
            model.syllabus_schedule[0].save()

            model.syllabus_schedule[1].schedule_type = current
            model.syllabus_schedule[1].save()

            model.syllabus_schedule[2].schedule_type = bad_status
            model.syllabus_schedule[2].save()

            url = reverse_lazy("admissions:academy_schedule") + f"?schedule_type={query}"
            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(model.syllabus_schedule[0]),
                get_serializer(model.syllabus_schedule[1]),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("admissions.SyllabusSchedule"),
                [
                    {
                        **self.bc.format.to_dict(model.syllabus_schedule[0]),
                        "schedule_type": current,
                    },
                    {
                        **self.bc.format.to_dict(model.syllabus_schedule[1]),
                        "schedule_type": current,
                    },
                    {
                        **self.bc.format.to_dict(model.syllabus_schedule[2]),
                        "schedule_type": bad_status,
                    },
                ],
            )

    """
    🔽🔽🔽 Syllabus slug in querystring
    """

    def test__syllabus_slug_in_querystring__bad_id(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
        )
        url = reverse_lazy("admissions:academy_schedule") + "?syllabus_slug=they-killed-kenny"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    def test__syllabus_slug_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)

        syllabus_kwargs = {"slug": "they-killed-kenny"}
        model = self.generate_models(
            authenticate=True,
            syllabus_schedule=True,
            profile_academy=True,
            capability="read_certificate",
            role="potato",
            syllabus=True,
            syllabus_kwargs=syllabus_kwargs,
        )
        url = reverse_lazy("admissions:academy_schedule") + "?syllabus_slug=they-killed-kenny"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.syllabus_schedule)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_syllabus_dict(), [{**self.model_to_dict(model, "syllabus")}])

    """
    🔽🔽🔽 Delete
    """

    def test_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ["id"]

        base = self.generate_models(academy=True)

        for field in many_fields:
            certificate_kwargs = {
                "logo": choice(["http://exampledot.com", "http://exampledotdot.com", "http://exampledotdotdot.com"]),
                "week_hours": randint(0, 999999999),
                "schedule_type": choice(["PAR-TIME", "FULL-TIME"]),
            }
            model = self.generate_models(
                authenticate=True,
                profile_academy=True,
                capability="crud_certificate",
                role="potato",
                certificate_kwargs=certificate_kwargs,
                syllabus=True,
                syllabus_schedule=True,
                models=base,
            )
            url = (
                reverse_lazy("admissions:academy_schedule")
                + f"?{field}="
                + str(getattr(model["syllabus_schedule"], field))
            )
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.delete(url)
        json = response.json()
        expected = {"detail": "Missing parameters in the querystring", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ["id"]

        base = self.generate_models(academy=True)

        for field in many_fields:
            certificate_kwargs = {
                "logo": choice(["http://exampledot.com", "http://exampledotdot.com", "http://exampledotdotdot.com"]),
                "week_hours": randint(0, 999999999),
                "schedule_type": choice(["PAR-TIME", "FULL-TIME"]),
            }
            model1 = self.generate_models(
                authenticate=True,
                profile_academy=True,
                capability="crud_certificate",
                role="potato",
                certificate_kwargs=certificate_kwargs,
                syllabus=True,
                syllabus_schedule=True,
                models=base,
            )

            model2 = self.generate_models(
                profile_academy=True,
                capability="crud_certificate",
                role="potato",
                certificate_kwargs=certificate_kwargs,
                syllabus=True,
                syllabus_schedule=True,
                models=base,
            )

            url = (
                reverse_lazy("admissions:academy_schedule")
                + f"?{field}="
                + str(getattr(model1["syllabus_schedule"], field))
                + ","
                + str(getattr(model2["syllabus_schedule"], field))
            )
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post__without_syllabus(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        response = self.client.post(url)
        json = response.json()
        expected = {
            "detail": "missing-syllabus-in-request",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post__syllabus_not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        data = {"syllabus": 1}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "detail": "syllabus-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post__without_academy(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        data = {"syllabus": 1}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "missing-academy-in-request", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post__academy_not_found(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        data = {"syllabus": 1, "academy": 2}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "academy-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post__without_body(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        data = {"syllabus": 1, "academy": 1}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "name": ["This field is required."],
            "description": ["This field is required."],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_syllabus_schedule_dict(), [])

    def test__post(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        data = {
            "academy": 1,
            "syllabus": 1,
            "name": "They killed kenny",
            "description": "Oh my god!",
        }
        response = self.client.post(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        del json["created_at"]

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "id": 1,
            "schedule_type": "PART-TIME",
            "syllabus": 1,
            **data,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    "id": 1,
                    "name": "They killed kenny",
                    "description": "Oh my god!",
                    "schedule_type": "PART-TIME",
                    "syllabus_id": 1,
                    "academy_id": 1,
                }
            ],
        )

    def test__post__passing_all_status__in_lowercase(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        schedule_type = random.choice(["PART-TIME", "FULL-TIME"])
        data = {
            "academy": 1,
            "syllabus": 1,
            "name": "They killed kenny",
            "description": "Oh my god!",
            "schedule_type": schedule_type.lower(),
        }
        response = self.client.post(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        del json["created_at"]

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "id": 1,
            "schedule_type": "PART-TIME",
            "syllabus": 1,
            **data,
            "schedule_type": schedule_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    "id": 1,
                    "name": "They killed kenny",
                    "description": "Oh my god!",
                    "schedule_type": "PART-TIME",
                    "syllabus_id": 1,
                    "academy_id": 1,
                    "schedule_type": schedule_type,
                }
            ],
        )

    def test__post__passing_all_status__in_uppercase(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, syllabus=True, capability="crud_certificate", role="potato"
        )
        url = reverse_lazy("admissions:academy_schedule")
        schedule_type = random.choice(["PART-TIME", "FULL-TIME"])
        data = {
            "academy": 1,
            "syllabus": 1,
            "name": "They killed kenny",
            "description": "Oh my god!",
            "schedule_type": schedule_type,
        }
        response = self.client.post(url, data, format="json")
        json = response.json()

        self.assertDatetime(json["created_at"])
        del json["created_at"]

        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        expected = {
            "id": 1,
            "schedule_type": "PART-TIME",
            "syllabus": 1,
            **data,
            "schedule_type": schedule_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_syllabus_schedule_dict(),
            [
                {
                    "id": 1,
                    "name": "They killed kenny",
                    "description": "Oh my god!",
                    "schedule_type": "PART-TIME",
                    "syllabus_id": 1,
                    "academy_id": 1,
                    "schedule_type": schedule_type,
                }
            ],
        )
