"""
Test /certificate
"""

from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""

    """
    🔽🔽🔽 Auth
    """

    def test_academy_cohort_sync_timeslot__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot")
        self.bc.database.create(authenticate=True)

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            "status_code": 403,
            "detail": "You (user: 1) don't have this capability: crud_certificate " "for academy 1",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without cohort in the querystring
    """

    def test_academy_cohort_sync_timeslot__without_cohort_in_querystring(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot")
        model = self.bc.database.create(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            "status_code": 400,
            "detail": "missing-cohort-in-querystring",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__with_cohort_in_querystring__without_certificate(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"
        model = self.bc.database.create(
            authenticate=True, profile_academy=True, capability="crud_certificate", role="potato"
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            "status_code": 400,
            "detail": "cohort-without-specialty-mode",
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_cohort_sync_timeslot__with_cohort_in_querystring__with_certificate(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"

        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            academy_kwargs=academy_kwargs,
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Academy without timezone
    """

    def test_academy_cohort_sync_timeslot__academy_without_timezone(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"
        model = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            syllabus_schedule_time_slot=True,
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {"detail": "without-timezone", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Without cohort timeslot
    """

    def test_academy_cohort_sync_timeslot__with_one_certificate_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"

        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            syllabus_schedule_time_slot=True,
            academy_kwargs=academy_kwargs,
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [
            {
                "id": 1,
                "cohort": model.cohort.id,
                "recurrent": model.syllabus_schedule_time_slot.recurrent,
                "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                "timezone": "America/Caracas",
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "id": 1,
                    "cohort_id": model.cohort.id,
                    "removed_at": model.syllabus_schedule_time_slot.removed_at,
                    "starting_at": model.syllabus_schedule_time_slot.starting_at,
                    "ending_at": model.syllabus_schedule_time_slot.ending_at,
                    "recurrent": model.syllabus_schedule_time_slot.recurrent,
                    "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                    "timezone": "America/Caracas",
                }
            ],
        )

    def test_academy_cohort_sync_timeslot__with_two_certificate_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"
        academy_kwargs = {"timezone": "America/Caracas"}
        base = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            academy_kwargs=academy_kwargs,
        )

        models = [self.bc.database.create(syllabus_schedule_time_slot=True, models=base) for _ in range(0, 2)]

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [
            {
                "id": model.syllabus_schedule_time_slot.id,
                "cohort": model.cohort.id,
                "recurrent": model.syllabus_schedule_time_slot.recurrent,
                "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                "timezone": "America/Caracas",
            }
            for model in models
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "id": model.syllabus_schedule_time_slot.id,
                    "cohort_id": model.cohort.id,
                    "removed_at": model.syllabus_schedule_time_slot.removed_at,
                    "starting_at": model.syllabus_schedule_time_slot.starting_at,
                    "ending_at": model.syllabus_schedule_time_slot.ending_at,
                    "recurrent": model.syllabus_schedule_time_slot.recurrent,
                    "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                    "timezone": "America/Caracas",
                }
                for model in models
            ],
        )

    """
    🔽🔽🔽 With two cohorts
    """

    def test_academy_cohort_sync_timeslot__with_two_certificate_timeslot__with_two_cohort(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1,2"
        academy_kwargs = {"timezone": "America/Caracas"}
        base = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            skip_cohort=True,
            academy_kwargs=academy_kwargs,
        )

        cohorts = [self.bc.database.create(cohort=True, models=base).cohort for _ in range(0, 2)]

        certificate_timeslots = [
            self.bc.database.create(syllabus_schedule_time_slot=True, models=base).syllabus_schedule_time_slot
            for _ in range(0, 2)
        ]

        data = {}
        response = self.client.post(url, data)
        json = response.json()

        # base = 0
        expected = [
            {
                "id": schedule_time_slot.id,
                "cohort": 1,
                "recurrent": schedule_time_slot.recurrent,
                "recurrency_type": schedule_time_slot.recurrency_type,
                "timezone": "America/Caracas",
            }
            for schedule_time_slot in certificate_timeslots
        ] + [
            {
                "id": schedule_time_slot.id + 2,
                "cohort": 2,
                "recurrent": schedule_time_slot.recurrent,
                "recurrency_type": schedule_time_slot.recurrency_type,
                "timezone": "America/Caracas",
            }
            for schedule_time_slot in certificate_timeslots
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "id": schedule_time_slot.id,
                    "cohort_id": 1,
                    "removed_at": schedule_time_slot.removed_at,
                    "starting_at": schedule_time_slot.starting_at,
                    "ending_at": schedule_time_slot.ending_at,
                    "recurrent": schedule_time_slot.recurrent,
                    "recurrency_type": schedule_time_slot.recurrency_type,
                    "timezone": "America/Caracas",
                }
                for schedule_time_slot in certificate_timeslots
            ]
            + [
                {
                    "id": schedule_time_slot.id + 2,
                    "cohort_id": 2,
                    "removed_at": schedule_time_slot.removed_at,
                    "starting_at": schedule_time_slot.starting_at,
                    "ending_at": schedule_time_slot.ending_at,
                    "recurrent": schedule_time_slot.recurrent,
                    "recurrency_type": schedule_time_slot.recurrency_type,
                    "timezone": "America/Caracas",
                }
                for schedule_time_slot in certificate_timeslots
            ],
        )

    """
    🔽🔽🔽 With cohort timeslot
    """

    def test_academy_cohort_sync_timeslot__with_one_cohort_timeslot(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_sync_timeslot") + "?cohort=1"

        academy_kwargs = {"timezone": "America/Caracas"}
        model = self.bc.database.create(
            authenticate=True,
            profile_academy=True,
            capability="crud_certificate",
            role="potato",
            syllabus_schedule=True,
            syllabus=True,
            cohort_time_slot=True,
            syllabus_schedule_time_slot=True,
            academy_kwargs=academy_kwargs,
        )

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = [
            {
                "id": 2,
                "cohort": model.cohort.id,
                "recurrent": model.syllabus_schedule_time_slot.recurrent,
                "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                "timezone": "America/Caracas",
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.all_cohort_time_slot_dict(),
            [
                {
                    "id": 2,
                    "cohort_id": model.cohort.id,
                    "removed_at": model.syllabus_schedule_time_slot.removed_at,
                    "starting_at": model.syllabus_schedule_time_slot.starting_at,
                    "ending_at": model.syllabus_schedule_time_slot.ending_at,
                    "recurrent": model.syllabus_schedule_time_slot.recurrent,
                    "recurrency_type": model.syllabus_schedule_time_slot.recurrency_type,
                    "timezone": "America/Caracas",
                }
            ],
        )
