from unittest.mock import MagicMock

from breathecode.provisioning.actions import ensure_llm_user
from breathecode.provisioning.utils.llm_client import LLMClientError

from ..mixins import ProvisioningTestCase


class EnsureLLMUserTestSuite(ProvisioningTestCase):
    def test_ensure_llm_user_assigns_team_when_team_id_configured(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

        client = MagicMock()
        client.get_user_info.side_effect = LLMClientError("404 user not found")
        client.create_user.return_value = {"user_id": "ok"}
        client.add_user_to_team.return_value = True

        provisioning_llm = ensure_llm_user(model.user, model.provisioning_academy, client=client)

        self.assertIsNotNone(provisioning_llm)
        external_user_id = provisioning_llm.external_user_id
        client.create_user.assert_called_once()
        client.add_user_to_team.assert_called_once_with(team_id="team-1", user_ids=[external_user_id])

    def test_ensure_llm_user_skips_add_when_user_info_teams_already_include_team(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

        client = MagicMock()
        client.get_user_info.return_value = {"user_id": "exists", "user_info": {"teams": ["team-1"]}}
        ensure_llm_user(model.user, model.provisioning_academy, client=client)
        client.add_user_to_team.assert_not_called()

    def test_ensure_llm_user_adds_when_teams_known_but_missing_configured_team(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

        client = MagicMock()
        client.get_user_info.return_value = {"user_info": {"teams": ["other-team"]}}

        provisioning_llm = ensure_llm_user(model.user, model.provisioning_academy, client=client)
        client.add_user_to_team.assert_called_once_with(team_id="team-1", user_ids=[provisioning_llm.external_user_id])

    def test_ensure_llm_user_adds_when_teams_empty_missing_configured_team(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.vendor_settings = {"team_id": "team-1"}
        model.provisioning_academy.save()

        client = MagicMock()
        client.get_user_info.return_value = {"user_id": "exists", "user_info": {"teams": []}}

        provisioning_llm = ensure_llm_user(model.user, model.provisioning_academy, client=client)
        client.add_user_to_team.assert_called_once_with(team_id="team-1", user_ids=[provisioning_llm.external_user_id])

    def test_ensure_llm_user_skips_team_assignment_when_team_id_missing(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "litellm"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.vendor_settings = {}
        model.provisioning_academy.save()

        client = MagicMock()
        client.get_user_info.return_value = {"user_id": "exists"}
        client.add_user_to_team.return_value = True

        ensure_llm_user(model.user, model.provisioning_academy, client=client)

        client.add_user_to_team.assert_not_called()
