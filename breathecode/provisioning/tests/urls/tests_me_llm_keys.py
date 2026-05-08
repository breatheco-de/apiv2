"""Tests for GET /provisioning/me/llm/keys."""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningLLM

from ..mixins import ProvisioningTestCase


class MeLLMKeysViewTestSuite(ProvisioningTestCase):
    @patch("breathecode.provisioning.views.get_llm_client")
    @patch("breathecode.provisioning.views.Consumable.list")
    def test_get_me_llm_keys_applies_key_then_user_priority(self, consumable_list_mock, get_llm_client_mock):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.api_url = "https://litellm.example.com"
        model.provisioning_vendor.save()

        ProvisioningLLM.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            external_user_id=f"{model.user.username}-{model.academy.slug}",
            status=ProvisioningLLM.STATUS_ACTIVE,
        )

        consumable_qs = MagicMock()
        consumable_qs.exists.return_value = True
        consumable_list_mock.return_value = consumable_qs

        get_user_info_payload = {
            "user_info": {
                "models": ["user/model-1"],
                "teams": ["team-1"],
            },
            "keys": [
                {
                    "token": "tok-a",
                    "key_alias": "key-with-user-fallback",
                    "models": [],
                    "metadata": {},
                    "spend": 1.2,
                    "created_at": "2026-01-01T00:00:00Z",
                    "team_id": None,
                },
                {
                    "token": "tok-b",
                    "key_alias": "key-specific-model",
                    "models": ["key/model-1"],
                    "metadata": {},
                    "spend": 0.3,
                    "created_at": "2026-01-02T00:00:00Z",
                    "team_id": "team-1",
                },
            ],
            "teams": [
                {
                    "team_id": "team-1",
                    "models": ["team/model-1", "team/model-2"],
                }
            ],
        }

        llm_client_mock = MagicMock()
        llm_client_mock.get_user_info.return_value = get_user_info_payload
        get_llm_client_mock.return_value = llm_client_mock

        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_llm_keys")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        by_token = {item["token_id"]: item for item in data}

        self.assertEqual(by_token["tok-a"]["models"], ["user/model-1"])
        self.assertEqual(by_token["tok-b"]["models"], ["key/model-1"])

    @patch("breathecode.provisioning.views.get_llm_client")
    @patch("breathecode.provisioning.views.Consumable.list")
    def test_get_me_llm_keys_falls_back_to_team_models_when_user_models_empty(
        self, consumable_list_mock, get_llm_client_mock
    ):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.api_url = "https://litellm.example.com"
        model.provisioning_vendor.save()

        ProvisioningLLM.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            external_user_id=f"{model.user.username}-{model.academy.slug}",
            status=ProvisioningLLM.STATUS_ACTIVE,
        )

        consumable_qs = MagicMock()
        consumable_qs.exists.return_value = True
        consumable_list_mock.return_value = consumable_qs

        llm_client_mock = MagicMock()
        llm_client_mock.get_user_info.return_value = {
            "user_info": {"models": [], "teams": ["team-1"]},
            "keys": [{"token": "tok-team", "models": [], "team_id": "team-1", "metadata": {}}],
            "teams": [{"team_id": "team-1", "models": ["team/model-1"]}],
        }
        get_llm_client_mock.return_value = llm_client_mock

        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_llm_keys")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["models"], ["team/model-1"])
