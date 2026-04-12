from unittest.mock import patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.admissions.models import CohortUser

from ...mixins.new_auth_test_case import AuthTestCase


class AcademyGithubCopilotTestSuite(AuthTestCase):
    def test_post_without_auth(self):
        url = reverse_lazy("authenticate:academy_github_copilot")
        response = self.client.post(url, data={"users": [1]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_without_capability(self):
        model = self.generate_models(authenticate=True, role="staff", profile_academy=True)
        self.bc.request.set_headers(academy=model["academy"].id)
        url = reverse_lazy("authenticate:academy_github_copilot")
        response = self.client.post(url, data={"users": [1]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_requires_users_or_cohort_id(self):
        model = self.generate_models(
            authenticate=True,
            role="staff",
            capability="manage_github_copilot_seats",
            profile_academy=True,
        )
        self.bc.request.set_headers(academy=model["academy"].id)
        url = reverse_lazy("authenticate:academy_github_copilot")
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_post_schedules_from_users_and_cohort_without_duplicates(self, mock_delay):
        model = self.generate_models(
            authenticate=True,
            role="staff",
            capability="manage_github_copilot_seats",
            profile_academy=True,
        )
        academy_id = model["academy"].id
        self.bc.request.set_headers(academy=academy_id)

        cohort = self.bc.database.create(academy=model["academy"], cohort=True).cohort

        eligible = self.bc.database.create(
            academy=model["academy"],
            user=True,
            credentials_github=True,
            credentials_github_kwargs={"username": "eligible"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        CohortUser.objects.create(user=eligible.user, cohort=cohort, educational_status="ACTIVE")

        pending = self.bc.database.create(
            academy=model["academy"],
            user=True,
            credentials_github=True,
            credentials_github_kwargs={"username": "pending-user"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "ADD"},
        )
        CohortUser.objects.create(user=pending.user, cohort=cohort, educational_status="ACTIVE")

        url = reverse_lazy("authenticate:academy_github_copilot")
        response = self.client.post(
            url,
            data={"users": [eligible.user.id], "cohort_id": cohort.id},
            format="json",
        )
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["total_requested"], 2)
        self.assertEqual(len(data["scheduled"]), 1)
        self.assertEqual(data["scheduled"][0]["user_id"], eligible.user.id)
        self.assertEqual(len(data["skipped"]), 1)
        self.assertEqual(data["skipped"][0]["user_id"], pending.user.id)
        self.assertEqual(data["skipped"][0]["reason"], "invalid_storage_status")
        self.assertEqual(mock_delay.call_count, 1)
