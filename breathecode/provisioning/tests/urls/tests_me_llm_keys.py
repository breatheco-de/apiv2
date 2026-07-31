"""Tests for GET /provisioning/me/llm/keys."""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningLLM

from ..mixins import ProvisioningTestCase


class MeLLMKeysViewTestSuite(ProvisioningTestCase):
    @patch("breathecode.provisioning.actions.get_llm_client")
    @patch("breathecode.provisioning.views.get_llm_client")
    @patch("breathecode.provisioning.views.Consumable.list")
    def test_get_me_llm_keys_applies_key_then_user_priority(
        self, consumable_list_mock, get_llm_client_views_mock, get_llm_client_actions_mock
    ):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.api_url = "https://litellm.example.com"
        model.provisioning_vendor.save()
        model.provisioning_academy.credentials_token = "test-token"
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

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
        llm_client_mock.get_team_info.return_value = {
            "team_memberships": [
                {
                    "user_id": f"{model.user.username}-{model.academy.slug}",
                    "spend": 1.5,
                    "litellm_budget_table": {"max_budget": 10.0},
                }
            ]
        }
        get_llm_client_views_mock.return_value = llm_client_mock
        get_llm_client_actions_mock.return_value = llm_client_mock

        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_llm_keys")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        by_token = {item["token_id"]: item for item in data}

        self.assertEqual(by_token["tok-a"]["models"], ["user/model-1"])
        self.assertEqual(by_token["tok-b"]["models"], ["key/model-1"])
        self.assertEqual(by_token["tok-a"]["host"], "https://litellm.example.com")
        self.assertEqual(by_token["tok-b"]["host"], "https://litellm.example.com")
        self.assertEqual(by_token["tok-a"]["vendor_name"], "litellm")
        self.assertEqual(by_token["tok-b"]["vendor_name"], "litellm")
        self.assertEqual(
            by_token["tok-a"]["member_budget"],
            {"spend": 1.5, "max": 10.0, "remaining": 8.5, "currency": "USD"},
        )
        self.assertEqual(by_token["tok-b"]["member_budget"], by_token["tok-a"]["member_budget"])

    @patch("breathecode.provisioning.actions.get_llm_client")
    @patch("breathecode.provisioning.views.get_llm_client")
    @patch("breathecode.provisioning.views.Consumable.list")
    def test_get_me_llm_keys_falls_back_to_team_models_when_user_models_empty(
        self, consumable_list_mock, get_llm_client_views_mock, get_llm_client_actions_mock
    ):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.api_url = "https://litellm.example.com"
        model.provisioning_vendor.save()
        model.provisioning_academy.credentials_token = "test-token"
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

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
        get_llm_client_views_mock.return_value = llm_client_mock
        get_llm_client_actions_mock.return_value = llm_client_mock

        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_llm_keys")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["models"], ["team/model-1"])
        self.assertEqual(response.json()[0]["host"], "https://litellm.example.com")
        self.assertEqual(response.json()[0]["vendor_name"], "litellm")

    @patch("breathecode.provisioning.views.resolve_provisioning_academy_for_llm")
    @patch("breathecode.provisioning.views.resolve_llm_client_and_external_id")
    def test_post_me_llm_keys_returns_models_with_fallback_to_empty(
        self, resolve_llm_client_mock, resolve_pa_for_llm_mock
    ):
        model = self.bc.database.create(user=1, academy=1)
        pa_llm_mock = MagicMock()
        pa_llm_mock.vendor.api_url = "https://litellm.example.com"
        pa_llm_mock.vendor.name = "LiteLLM"
        pa_llm_mock.vendor_settings = {"team_id": "team-abc"}
        resolve_pa_for_llm_mock.return_value = pa_llm_mock

        llm_client_mock = MagicMock()
        llm_client_mock.create_api_key.return_value = {
            "id": "tok-created",
            "key": "sk-xxx",
            "name": "alias",
            "created_at": "2026-01-03T00:00:00Z",
        }
        llm_client_mock.get_user_info.return_value = {
            "user_info": {"models": []},
            "keys": [],
            "teams": [],
        }
        resolve_llm_client_mock.return_value = (llm_client_mock, "external-user", 1, False)

        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:me_llm_keys")
        response = self.client.post(url, data={"key_alias": "alias"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["models"], [])
        self.assertEqual(response.json()["host"], "https://litellm.example.com")
        self.assertEqual(response.json()["vendor_name"], "LiteLLM")
        llm_client_mock.create_api_key.assert_called_once_with(
            external_user_id="external-user",
            name="alias",
            metadata=None,
            team_id="team-abc",
        )
        resolve_pa_for_llm_mock.assert_called_once()
        self.assertEqual(resolve_pa_for_llm_mock.call_args[0][0].pk, model.academy.pk)
