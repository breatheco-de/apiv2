"""Tests for LiteLLM client."""

from unittest.mock import MagicMock, patch

import pytest

from breathecode.services.litellm.client import LiteLLMClient, LiteLLMError


class TestLiteLLMClient:
    @patch("breathecode.services.litellm.client.requests.post")
    def test_create_api_key_sends_team_id_and_maps_expires(self, post_mock):
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "token_id": "tok-1",
            "key": "sk-test",
            "key_alias": "alias",
            "created_at": "2026-01-01T00:00:00Z",
            "expires": "2026-01-31T00:00:00Z",
        }
        post_mock.return_value = response_mock

        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")
        result = client.create_api_key(external_user_id="user-academy", team_id="team-1", name="alias")

        post_mock.assert_called_once()
        payload = post_mock.call_args.kwargs["json"]
        assert payload["team_id"] == "team-1"
        assert payload["duration"] == "30d"
        assert payload["user_id"] == "user-academy"
        assert result["expires"] == "2026-01-31T00:00:00Z"

    def test_create_api_key_requires_team_id(self):
        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")

        with pytest.raises(LiteLLMError, match="team_id is required"):
            client.create_api_key(external_user_id="user-academy", team_id="")

    @patch("breathecode.services.litellm.client.requests.get")
    def test_list_keys_normalizes_token_to_token_id(self, get_mock):
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "keys": [
                {"token": "tok-a", "user_id": "student-miami", "team_id": "team-1"},
                {"token_id": "tok-b", "user_id": "other-miami", "team_id": "team-1"},
            ],
            "page": 1,
            "total_pages": 2,
            "total_count": 3,
        }
        get_mock.return_value = response_mock

        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")
        result = client.list_keys(page=1, size=100, team_id="team-1")

        get_mock.assert_called_once()
        params = get_mock.call_args.kwargs["params"]
        assert params["return_full_object"] == "true"
        assert params["page"] == 1
        assert params["size"] == 100
        assert params["team_id"] == "team-1"
        assert result["total_pages"] == 2
        assert result["keys"][0]["token_id"] == "tok-a"
        assert result["keys"][1]["token_id"] == "tok-b"

    @patch("breathecode.services.litellm.client.requests.get")
    def test_list_users_returns_paginated_users(self, get_mock):
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "users": [
                {
                    "user_id": "student-miami",
                    "user_role": "internal_user_viewer",
                    "teams": ["team-1"],
                    "key_count": 1,
                }
            ],
            "page": 1,
            "page_size": 100,
            "total_pages": 2,
            "total": 150,
        }
        get_mock.return_value = response_mock

        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")
        result = client.list_users(page=1, page_size=100)

        get_mock.assert_called_once()
        params = get_mock.call_args.kwargs["params"]
        assert params == {"page": 1, "page_size": 100}
        assert result["total_pages"] == 2
        assert result["users"][0]["user_id"] == "student-miami"

    @patch("breathecode.services.litellm.client.requests.post")
    def test_update_key_sends_duration(self, post_mock):
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"key": "tok-a", "expires": "2026-02-01T00:00:00Z"}
        post_mock.return_value = response_mock

        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")
        result = client.update_key(key="tok-a", duration="30d")

        post_mock.assert_called_once()
        payload = post_mock.call_args.kwargs["json"]
        assert payload == {"key": "tok-a", "duration": "30d"}
        assert result["expires"] == "2026-02-01T00:00:00Z"

    def test_update_key_requires_key(self):
        client = LiteLLMClient(base_url="https://litellm.example.com", api_key="master-key")

        with pytest.raises(LiteLLMError, match="key is required"):
            client.update_key(key="", duration="30d")
