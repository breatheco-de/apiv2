"""
Test cases for POST /v1/auth/academy/student/invite/bulk and GET /v1/auth/academy/student/invite/bulk/<job_id>
"""

from unittest.mock import MagicMock, patch

from django.core.cache.backends.locmem import LocMemCache
from django.urls import reverse_lazy
from rest_framework import status

from breathecode.authenticate.utils.bulk_student_manager import (
    get_bulk_job_key,
    set_bulk_job_state,
)
from breathecode.tests.mixins import GenerateModelsMixin

from ...mixins.new_auth_test_case import AuthTestCase

ACTIVE_ACADEMY = {"status": "ACTIVE"}
OPEN_COHORT = {"stage": "STARTED", "available_as_saas": True}


class BulkStudentUploadViewTestSuite(AuthTestCase):
    """Bulk student upload view tests."""

    def test_bulk_post_without_auth(self):
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": [{"email": "a@a.com", "first_name": "A", "last_name": "B", "cohort_id": 1}]},
            format="json",
            headers={"academy": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_post_without_academy_header(self):
        self.bc.database.create(authenticate=True, capability="crud_student", profile_academy=True)
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": [{"email": "a@a.com", "first_name": "A", "last_name": "B", "cohort_id": 1}]},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

    def test_bulk_post_missing_cohort_id_fails_only_that_row(self):
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=OPEN_COHORT,
            role="student",
        )
        url = reverse_lazy("authenticate:academy_student_bulk") + "?soft=true"
        response = self.client.post(
            url,
            {
                "students": [
                    {"email": "a@a.com", "first_name": "A", "last_name": "B"},
                    {"email": "b@b.com", "first_name": "B", "last_name": "C", "cohort_id": 1},
                ]
            },
            format="json",
            headers={"academy": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(results[0]["status"], "failed")
        self.assertEqual(results[0]["slug"], "cohort-id-required")
        self.assertEqual(results[1]["status"], "created")

    def test_bulk_post_invalid_student_row(self):
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            role="student",
        )
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(url, {"students": ["a@a.com"]}, format="json", headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("detail"), "invalid-student-row")

    def test_bulk_post_soft_plan_not_in_cohort_fails_only_that_row(self):
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=[OPEN_COHORT, OPEN_COHORT],
            role="student",
            cohort_set=1,
            cohort_set_cohort={"cohort_id": 1},
            plan={"status": "ACTIVE", "cohort_set_id": 1},
        )
        cohort_in_plan, cohort_outside_plan = model.cohort
        url = reverse_lazy("authenticate:academy_student_bulk") + "?soft=true"
        response = self.client.post(
            url,
            {
                "students": [
                    {"email": "ok@example.com", "first_name": "Ok", "cohort_id": cohort_in_plan.id, "plans": [1]},
                    {
                        "email": "bad@example.com",
                        "first_name": "Bad",
                        "cohort_id": cohort_outside_plan.id,
                        "plans": [1],
                    },
                ]
            },
            format="json",
            headers={"academy": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(results[0]["status"], "created")
        self.assertEqual(results[1]["status"], "failed")
        self.assertEqual(results[1]["slug"], "plan-cohort-mismatch")
        self.assertEqual(results[1]["email"], "bad@example.com")
        self.assertIn(cohort_outside_plan.slug, results[1]["message"])

    def test_bulk_post_empty_students(self):
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=OPEN_COHORT,
            role="student",
        )
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": []},
            format="json",
            headers={"academy": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("detail"), "students-required")

    def test_bulk_post_soft_run_returns_200_with_results(self):
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=OPEN_COHORT,
            role="student",
        )
        url = reverse_lazy("authenticate:academy_student_bulk") + "?soft=true"
        response = self.client.post(
            url,
            {
                "students": [
                    {"email": "new@example.com", "first_name": "New", "last_name": "User", "cohort_id": 1},
                    {"email": model.user.email, "first_name": "Existing", "last_name": "User", "cohort_id": 1},
                ],
            },
            format="json",
            headers={"academy": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json = response.json()
        self.assertEqual(json["total"], 2)
        self.assertEqual(len(json["results"]), 2)
        for r in json["results"]:
            self.assertIn("index", r)
            self.assertIn("email", r)
            self.assertIn("classification", r)
            self.assertIn("status", r)
        self.assertEqual(len(self.bc.database.list_of("authenticate.ProfileAcademy")), 1)
        self.assertEqual(len(self.bc.database.list_of("admissions.CohortUser")), 0)

    def test_bulk_post_normal_returns_202_and_job_id(self):
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=OPEN_COHORT,
            role="student",
        )
        url = reverse_lazy("authenticate:academy_student_bulk")
        with patch("breathecode.authenticate.tasks.process_bulk_student_upload") as mock_delay:
            mock_delay.delay = MagicMock(return_value=None)
            response = self.client.post(
                url,
                {
                    "students": [
                        {"email": "new@example.com", "first_name": "New", "last_name": "User", "cohort_id": 1},
                    ],
                },
                format="json",
                headers={"academy": 1},
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        json = response.json()
        self.assertIn("job_id", json)
        self.assertEqual(json["status"], "pending")
        self.assertEqual(json["total"], 1)
        mock_delay.delay.assert_called_once()

    def test_bulk_get_job_not_found(self):
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            role="student",
        )
        url = reverse_lazy(
            "authenticate:academy_student_bulk_id", kwargs={"job_id": "00000000-0000-0000-0000-000000000001"}
        )
        response = self.client.get(url, headers={"academy": 1})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json().get("detail"), "job-not-found")

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_bulk_post_then_get_job_returns_completed_with_results(self):
        """POST bulk → task runs synchronously → GET job returns completed with one created, one skipped."""
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=ACTIVE_ACADEMY,
            cohort=OPEN_COHORT,
            cohort_user=1,
            role="student",
        )
        students = [
            {"email": "new@example.com", "first_name": "New", "last_name": "User", "cohort_id": model.cohort.id},
            {"email": model.user.email, "first_name": "Existing", "last_name": "User", "cohort_id": model.cohort.id},
        ]

        # the job state is skipped on the test fake cache, a real in-memory cache keeps it between requests
        with patch("django.core.cache.cache", LocMemCache("bulk-student-upload", {})):
            url = reverse_lazy("authenticate:academy_student_bulk")
            response = self.client.post(
                url,
                {"students": students},
                format="json",
                headers={"academy": 1},
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.content)
            job_id = response.json()["job_id"]

            get_url = reverse_lazy("authenticate:academy_student_bulk_id", kwargs={"job_id": job_id})
            get_response = self.client.get(get_url, headers={"academy": 1})
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        data = get_response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["processed"], 2)
        self.assertEqual(len(data["results"]), 2)
        statuses = [r["status"] for r in data["results"]]
        self.assertIn("created", statuses)
        self.assertIn("skipped", statuses)
        for r in data["results"]:
            self.assertIn("index", r)
            self.assertIn("email", r)
            self.assertIn("classification", r)
