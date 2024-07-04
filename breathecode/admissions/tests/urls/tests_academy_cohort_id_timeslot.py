"""
Test /cohort/user
"""

import random
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.utils import DatetimeInteger
from ..mixins import AdmissionsTestCase


def get_serializer(self, cohort_time_slot):
    return {
        "id": cohort_time_slot.id,
        "cohort": cohort_time_slot.cohort.id,
        "starting_at": self.integer_to_iso(cohort_time_slot.timezone, cohort_time_slot.starting_at),
        "ending_at": self.integer_to_iso(cohort_time_slot.timezone, cohort_time_slot.ending_at),
        "recurrent": cohort_time_slot.recurrent,
        "recurrency_type": cohort_time_slot.recurrency_type,
        "created_at": self.datetime_to_iso(cohort_time_slot.created_at),
        "updated_at": self.datetime_to_iso(cohort_time_slot.updated_at),
    }


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 Auth
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__without_auth(self):
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__without_academy_header(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
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

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__without_capabilities(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
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

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__without_data(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato"
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__with_data(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato", cohort_time_slot=True
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(self, model.cohort_time_slot)]

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
    🔽🔽🔽 recurrency_type in querystring
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__recurrency_type_in_querystring__not_found(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato", cohort_time_slot=True
        )

        url = (
            reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
            + f"?recurrency_type=asdasdasd"
        )
        response = self.client.get(url)
        json = response.json()
        expected = []

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

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__recurrency_type_in_querystring__found(self):
        statuses = ["DAILY", "WEEKLY", "MONTHLY"]
        cases = [(x, x, random.choice([y for y in statuses if x != y])) for x in statuses] + [
            (x, x.lower(), random.choice([y for y in statuses if x != y])) for x in statuses
        ]

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_all_cohort", role="potato", cohort_time_slot=3
        )

        for current, query, bad_status in cases:
            model.cohort_time_slot[0].recurrency_type = current
            model.cohort_time_slot[0].save()

            model.cohort_time_slot[1].recurrency_type = current
            model.cohort_time_slot[1].save()

            model.cohort_time_slot[2].recurrency_type = bad_status
            model.cohort_time_slot[2].save()

            url = (
                reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
                + f"?recurrency_type={query}"
            )

            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(self, model.cohort_time_slot[0]),
                get_serializer(self, model.cohort_time_slot[1]),
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.all_cohort_time_slot_dict(),
                [
                    {
                        **self.bc.format.to_dict(model.cohort_time_slot[0]),
                        "recurrency_type": current,
                    },
                    {
                        **self.bc.format.to_dict(model.cohort_time_slot[1]),
                        "recurrency_type": current,
                    },
                    {
                        **self.bc.format.to_dict(model.cohort_time_slot[2]),
                        "recurrency_type": bad_status,
                    },
                ],
            )

    """
    🔽🔽🔽 Without timezone
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__post__without_timezone(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_cohort", role="potato")
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
        data = {}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {"detail": "academy-without-timezone", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Post
    """

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__post__without_ending_at_and_starting_at(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})
        data = {}
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "ending_at": ["This field is required."],
            "starting_at": ["This field is required."],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__post__passing_all_status__in_lowercase(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()

        recurrency_type = random.choice(["DAILY", "WEEKLY", "MONTHLY"])
        data = {
            "ending_at": self.datetime_to_iso(ending_at),
            "starting_at": self.datetime_to_iso(starting_at),
            "recurrency_type": recurrency_type.lower(),
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "cohort": 1,
            "id": 1,
            "recurrent": True,
            "timezone": "America/Caracas",
            "recurrency_type": recurrency_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "cohort_id": 1,
                    "removed_at": None,
                    "ending_at": DatetimeInteger.from_datetime(model.academy.timezone, ending_at),
                    "id": 1,
                    "recurrent": True,
                    "starting_at": DatetimeInteger.from_datetime(model.academy.timezone, starting_at),
                    "timezone": "America/Caracas",
                    "recurrency_type": recurrency_type,
                }
            ],
        )

    @patch("breathecode.events.tasks.build_live_classes_from_timeslot.delay", MagicMock())
    def test__post__passing_all_status__in_uppercase(self):
        self.headers(academy=1)
        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            academy_kwargs=academy_kwargs,
        )
        url = reverse_lazy("admissions:academy_cohort_id_timeslot", kwargs={"cohort_id": 1})

        starting_at = self.datetime_now()
        ending_at = self.datetime_now()

        recurrency_type = random.choice(["DAILY", "WEEKLY", "MONTHLY"])
        data = {
            "ending_at": self.datetime_to_iso(ending_at),
            "starting_at": self.datetime_to_iso(starting_at),
            "recurrency_type": recurrency_type,
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = {
            "cohort": 1,
            "id": 1,
            "recurrent": True,
            "timezone": "America/Caracas",
            "recurrency_type": recurrency_type,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "cohort_id": 1,
                    "removed_at": None,
                    "ending_at": DatetimeInteger.from_datetime(model.academy.timezone, ending_at),
                    "id": 1,
                    "recurrent": True,
                    "starting_at": DatetimeInteger.from_datetime(model.academy.timezone, starting_at),
                    "timezone": "America/Caracas",
                    "recurrency_type": recurrency_type,
                }
            ],
        )
