"""
Test cases for POST /v1/auth/academy/student/invite/bulk and GET /v1/auth/academy/student/invite/bulk/<job_id>
"""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.authenticate.utils.bulk_student_manager import (
    get_bulk_job_key,
    set_bulk_job_state,
)
from breathecode.authenticate.tasks import process_bulk_student_upload
from breathecode.tests.mixins import GenerateModelsMixin

from ...mixins.new_auth_test_case import AuthTestCase


class BulkStudentUploadViewTestSuite(AuthTestCase):
    """Bulk student upload view tests."""

    def test_bulk_post_without_auth(self):
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": [{"email": "a@a.com", "first_name": "A", "last_name": "B", "cohort_id": 1}]},
            format="json",
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

    def test_bulk_post_missing_cohort_id(self):
        self.headers(academy=1)
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
        )
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": [{"email": "a@a.com", "first_name": "A", "last_name": "B"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("slug"), "cohort-id-required")

    def test_bulk_post_empty_students(self):
        self.headers(academy=1)
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
            cohort=1,
        )
        url = reverse_lazy("authenticate:academy_student_bulk")
        response = self.client.post(
            url,
            {"students": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("slug"), "students-required")

    def test_bulk_post_soft_run_returns_200_with_results(self):
        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
            cohort=1,
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
        self.headers(academy=1)
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
            cohort=1,
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
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        json = response.json()
        self.assertIn("job_id", json)
        self.assertEqual(json["status"], "pending")
        self.assertEqual(json["total"], 1)
        mock_delay.delay.assert_called_once()

    def test_bulk_get_job_not_found(self):
        self.headers(academy=1)
        self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
        )
        url = reverse_lazy("authenticate:academy_student_bulk_id", kwargs={"job_id": "00000000-0000-0000-0000-000000000001"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json().get("slug"), "job-not-found")

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_bulk_post_then_get_job_returns_completed_with_results(self):
        """POST bulk → task runs synchronously → GET job returns completed with one created, one skipped."""
        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_student",
            profile_academy=True,
            academy=1,
            cohort=2,
            role="student",
        )
        cohort1 = model.cohort
        cohort2 = self.bc.database.create(cohort=1, academy=model.academy).cohort
        self.bc.database.create(cohort_user=1, user=model.user, cohort=cohort2)
        students = [
            {"email": "new@example.com", "first_name": "New", "last_name": "User", "cohort_id": cohort1.id},
            {"email": model.user.email, "first_name": "Existing", "last_name": "User", "cohort_id": cohort1.id},
        ]

        def run_task_sync(*args, **kwargs):
            process_bulk_student_upload(*args, **kwargs)

        with patch("breathecode.authenticate.tasks.process_bulk_student_upload") as mock_task:
            mock_task.delay = run_task_sync
            url = reverse_lazy("authenticate:academy_student_bulk")
            response = self.client.post(
                url,
                {"students": students},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        job_id = response.json()["job_id"]

        get_url = reverse_lazy("authenticate:academy_student_bulk_id", kwargs={"job_id": job_id})
        get_response = self.client.get(get_url)
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
