from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db.models import Q
from django.utils import timezone as django_timezone

from breathecode.payments import actions


def _mock_consumable_budget(total):
    mock_qs = MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.exclude.return_value = mock_qs
    mock_qs.aggregate.return_value = {"total": total}
    return mock_qs


class TestSyncLlmMemberBudgetToLlmProvider:
    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_align_calls_member_update_and_persists(self, mock_timezone, mock_consumable_list):
        mock_timezone.now.return_value = MagicMock()
        mock_consumable_list.return_value = _mock_consumable_budget(1000)

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = ""
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1
        provisioning_llm.id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        client.get_team_info.return_value = {
            "team_info": {
                "team_member_budget_table": {
                    "tpm_limit": 1000,
                    "rpm_limit": 2,
                }
            },
            "team_memberships": [
                {
                    "user_id": "user-academy",
                    "spend": 0.5,
                }
            ],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
            team_data=client.get_team_info.return_value,
        )

        mock_consumable_list.assert_called_once_with(
            user=1,
            service="llm-budget",
            include_zero_balance=False,
        )
        client.update_team_member.assert_called_once_with(
            team_id="team-1",
            user_id="user-academy",
            max_budget_in_team=Decimal("10.5"),
            budget_duration=None,
            tpm_limit=1000,
            rpm_limit=2,
        )
        client.get_team_info.assert_not_called()
        provisioning_llm.save.assert_called()

    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_fetches_team_data_when_not_provided(self, mock_timezone, mock_consumable_list):
        mock_timezone.now.return_value = MagicMock()
        mock_consumable_list.return_value = _mock_consumable_budget(1000)

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = ""
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1
        provisioning_llm.id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        client.get_team_info.return_value = {
            "team_info": {"team_member_budget_table": {"tpm_limit": 1, "rpm_limit": 2}},
            "team_memberships": [{"user_id": "user-academy", "spend": 0}],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
        )

        client.get_team_info.assert_called_once_with(team_id="team-1")

    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_skips_member_update_when_no_active_budget(self, mock_timezone, mock_consumable_list):
        mock_timezone.now.return_value = MagicMock()
        mock_consumable_list.return_value = _mock_consumable_budget(0)

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        client.get_team_info.return_value = {
            "team_memberships": [{"user_id": "user-academy", "spend": 0}],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
            team_data=client.get_team_info.return_value,
        )

        client.update_team_member.assert_not_called()
        assert provisioning_llm.last_budget_sync_error.startswith("LLM budget sync skipped:")
        provisioning_llm.save.assert_called_with(
            update_fields=["last_budget_sync_error", "updated_at"]
        )

    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_align_reads_tpm_rpm_from_team_member_budget_table(self, mock_timezone, mock_consumable_list):
        mock_timezone.now.return_value = MagicMock()
        mock_consumable_list.return_value = _mock_consumable_budget(1000)

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = ""
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1
        provisioning_llm.id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        client.get_team_info.return_value = {
            "team_info": {
                "team_member_budget_table": {
                    "tpm_limit": 1,
                    "rpm_limit": None,
                }
            },
            "team_memberships": [
                {
                    "user_id": "user-academy",
                    "spend": 0.5,
                    "litellm_budget_table": {
                        "tpm_limit": None,
                        "rpm_limit": 10,
                    },
                }
            ],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
        )

        client.update_team_member.assert_called_once_with(
            team_id="team-1",
            user_id="user-academy",
            max_budget_in_team=Decimal("10.5"),
            budget_duration=None,
            tpm_limit=1,
            rpm_limit=None,
        )

    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_align_falls_back_to_member_budget_when_team_template_is_null(
        self, mock_timezone, mock_consumable_list
    ):
        mock_timezone.now.return_value = MagicMock()
        mock_consumable_list.return_value = _mock_consumable_budget(1000)

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = ""
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1
        provisioning_llm.id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        client.get_team_info.return_value = {
            "team_info": {
                "team_member_budget_table": None,
            },
            "team_memberships": [
                {
                    "user_id": "user-academy",
                    "spend": 0.5,
                    "litellm_budget_table": {
                        "tpm_limit": 1000,
                        "rpm_limit": 2,
                    },
                }
            ],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
        )

        client.update_team_member.assert_called_once_with(
            team_id="team-1",
            user_id="user-academy",
            max_budget_in_team=Decimal("10.5"),
            budget_duration=None,
            tpm_limit=1000,
            rpm_limit=2,
        )

    @patch("breathecode.payments.actions.Consumable.list")
    @patch("breathecode.payments.actions.timezone")
    def test_excludes_consumables_expiring_within_renew_window_from_budget_sum(
        self, mock_timezone, mock_consumable_list
    ):
        fixed_now = django_timezone.now()
        mock_timezone.now.return_value = fixed_now
        mock_qs = _mock_consumable_budget(1000)
        mock_consumable_list.return_value = mock_qs

        provisioning_llm = MagicMock()
        provisioning_llm.external_user_id = "user-academy"
        provisioning_llm.last_known_spend = Decimal("0")
        provisioning_llm.litellm_team_id = ""
        provisioning_llm.user_id = 1
        provisioning_llm.academy_id = 1
        provisioning_llm.id = 1

        provisioning_academy = MagicMock()
        provisioning_academy.vendor_settings = {"team_id": "team-1"}

        client = MagicMock()
        team_data = {
            "team_memberships": [{"user_id": "user-academy", "spend": 3}],
        }

        actions.sync_llm_member_budget_to_llm_provider(
            provisioning_llm,
            provisioning_academy,
            client,
            team_data=team_data,
        )

        sub_cutoff = fixed_now + timedelta(hours=1)
        pf_cutoff = fixed_now + timedelta(hours=2)
        assert mock_qs.filter.call_count == 2
        renew_filter = mock_qs.filter.call_args_list[1][0][0]
        assert renew_filter == (
            Q(subscription__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=sub_cutoff))
            | Q(subscription_seat__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=sub_cutoff))
            | Q(plan_financing__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=pf_cutoff))
            | Q(plan_financing_seat__isnull=False)
            & (Q(valid_until__isnull=True) | Q(valid_until__gt=pf_cutoff))
            | Q(standalone_invoice__isnull=False)
        )
        client.update_team_member.assert_called_once_with(
            team_id="team-1",
            user_id="user-academy",
            max_budget_in_team=Decimal("13"),
            budget_duration=None,
            tpm_limit=None,
            rpm_limit=None,
        )
