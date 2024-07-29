"""
Test /cohort/user
"""

import random
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 Auth
    """

    def test_cohort_time_slot__without_auth(self):
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_time_slot__without_academy_header(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_time_slot__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: read_all_cohort for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without data
    """

    def test_cohort_time_slot__without_data(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato"
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "time-slot-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 With data
    """

    def test_cohort_time_slot__with_data(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato", cohort_time_slot=True
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            "id": model.cohort_time_slot.id,
            "cohort": model.cohort_time_slot.cohort.id,
            "starting_at": self.integer_to_iso(model.cohort_time_slot.timezone, model.cohort_time_slot.starting_at),
            "ending_at": self.integer_to_iso(model.cohort_time_slot.timezone, model.cohort_time_slot.ending_at),
            "recurrent": model.cohort_time_slot.recurrent,
            "recurrency_type": model.cohort_time_slot.recurrency_type,
            "created_at": self.datetime_to_iso(model.cohort_time_slot.created_at),
            "updated_at": self.datetime_to_iso(model.cohort_time_slot.updated_at),
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    **self.model_to_dict(model, "cohort_time_slot"),
                }
            ],
        )

    """
    🔽🔽🔽 Put
    """

    def test_cohort_time_slot__put__without_time_slot(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_cohort", role="potato")
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        data = {}
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "detail": "time-slot-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_time_slot__put__without_timezone(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_cohort", role="potato", cohort_time_slot=True
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        data = {}
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "academy-without-timezone", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    **self.model_to_dict(model, "cohort_time_slot"),
                }
            ],
        )

    def test_cohort_time_slot__put__without_ending_at_and_starting_at(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            cohort_time_slot=True,
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        data = {}
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "ending_at": ["This field is required."],
            "starting_at": ["This field is required."],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    **self.model_to_dict(model, "cohort_time_slot"),
                }
            ],
        )

    def test_cohort_time_slot__put__in_lowercase(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            cohort_time_slot=True,
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()

        recurrency_type = random.choice(["DAILY", "WEEKLY", "MONTHLY"])
        data = {
            "ending_at": self.datetime_to_iso(ending_at),
            "starting_at": self.datetime_to_iso(starting_at),
            "recurrency_type": recurrency_type.lower(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "cohort": 1,
            "id": 1,
            "recurrent": True,
            "timezone": model.academy.timezone,
            "recurrency_type": recurrency_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    **self.model_to_dict(model, "cohort_time_slot"),
                    "ending_at": self.datetime_to_integer(model.academy.timezone, ending_at),
                    "starting_at": self.datetime_to_integer(model.academy.timezone, starting_at),
                    "timezone": model.academy.timezone,
                    "recurrency_type": recurrency_type,
                }
            ],
        )

    def test_cohort_time_slot__put__in_uppercase(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            cohort_time_slot=True,
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()

        recurrency_type = random.choice(["DAILY", "WEEKLY", "MONTHLY"])
        data = {
            "ending_at": self.datetime_to_iso(ending_at),
            "starting_at": self.datetime_to_iso(starting_at),
            "recurrency_type": recurrency_type,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "cohort": 1,
            "id": 1,
            "recurrent": True,
            "timezone": model.academy.timezone,
            "recurrency_type": recurrency_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    **self.model_to_dict(model, "cohort_time_slot"),
                    "ending_at": self.datetime_to_integer(model.academy.timezone, ending_at),
                    "starting_at": self.datetime_to_integer(model.academy.timezone, starting_at),
                    "timezone": model.academy.timezone,
                    "recurrency_type": recurrency_type,
                }
            ],
        )

    """
    🔽🔽🔽 Delete
    """

    def test_cohort_time_slot__delete__without_time_slot(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_cohort", role="potato")
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.delete(url)
        json = response.json()
        expected = {
            "detail": "time-slot-not-found",
            "status_code": 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_cohort_time_slot__delete(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_cohort", role="potato", cohort_time_slot=True
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot_id", kwargs={"cohort_id": 1, "timeslot_id": 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])
