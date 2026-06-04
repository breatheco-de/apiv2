"""Tests for GET /provisioning/academy/admin/llm/teams."""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningAcademy

from ..mixins import ProvisioningTestCase


class AcademyAdminLLMTeamsViewTestSuite(ProvisioningTestCase):
    @patch("breathecode.provisioning.views.get_llm_client")
    def test_get_admin_llm_teams_returns_normalized_payload(self, get_llm_client_mock):
        model = self.bc.database.create(
            user=1,
            academy=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.api_url = "https://litellm.example.com"
        model.provisioning_vendor.save()
        ProvisioningAcademy.objects.create(
            academy=model.academy,
            vendor=model.provisioning_vendor,
            credentials_token="token",
        )

        llm_client_mock = MagicMock()
        llm_client_mock.list_teams.return_value = {
            "teams": [
                {
                    "team_id": "team-1",
                    "team_alias": "AI Engineering",
                    "models": ["groq/llama-3.1-8b-instant"],
                    "max_budget": 5.0,
                    "budget_duration": "30d",
                    "budget_reset_at": "2026-06-01T00:00:00Z",
                    "spend": 1.25,
                    "blocked": False,
                    "members_with_roles": [{"user_id": "u1", "role": "admin"}],
                }
            ]
        }
        get_llm_client_mock.return_value = llm_client_mock

        self.client.force_authenticate(model.user)
        self.headers(academy=model.academy.id)
        url = reverse_lazy("provisioning:academy_admin_llm_teams")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "team_id": "team-1",
                    "team_alias": "AI Engineering",
                    "models": ["groq/llama-3.1-8b-instant"],
                    "max_budget": 5.0,
                    "budget_duration": "30d",
                    "budget_reset_at": "2026-06-01T00:00:00Z",
                    "spend": 1.25,
                    "blocked": False,
                }
            ],
        )

    def test_get_admin_llm_teams_requires_capability(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        self.headers(academy=model.academy.id)
        url = reverse_lazy("provisioning:academy_admin_llm_teams")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
