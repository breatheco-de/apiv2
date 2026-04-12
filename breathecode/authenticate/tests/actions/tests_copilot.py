"""Tests for GitHub Copilot seat sync (GithubAcademyUser + API)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from breathecode.authenticate.actions import (
    COPILOT_REVOKE_DELAY_SECONDS,
    grant_copilot_seat_for_user,
    reconcile_copilot_seats_for_org,
    schedule_copilot_grants_for_academy_users,
    resolve_github_username,
    revoke_copilot_seat_after_delay,
)
from breathecode.authenticate.models import GithubAcademyUser
from breathecode.authenticate.receivers import github_academy_user_copilot_schedule
from ..mixins.new_auth_test_case import AuthTestCase


def set_copilot_mode(academy, mode):
    features = academy.get_academy_features()
    features["commerce"]["copilot_provisioning"] = mode
    academy.academy_features = features
    academy.save(update_fields=["academy_features"])


class GithubAcademyUserStorageLogTestSuite(AuthTestCase):
    def test_log_keeps_last_five_entries_with_timestamps(self):
        models = self.bc.database.create(user=True, academy=True, github_academy_user=True)
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        for i in range(7):
            gau.log(f"step-{i}")
        self.assertEqual(len(gau.storage_log), GithubAcademyUser.STORAGE_LOG_MAX_ENTRIES)
        msgs = [e["msg"] for e in gau.storage_log]
        self.assertEqual(msgs, ["step-2", "step-3", "step-4", "step-5", "step-6"])
        self.assertTrue(all("at" in e and e["at"] for e in gau.storage_log))

    def test_log_reset_true_replaces_history_with_single_entry(self):
        models = self.bc.database.create(user=True, academy=True, github_academy_user=True)
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        gau.log("first")
        gau.log("second", reset=True)
        self.assertEqual([e["msg"] for e in gau.storage_log], ["second"])


class CopilotActionsHelpersTestSuite(AuthTestCase):
    def test_resolve_github_username_prefers_credentials(self):
        models = self.bc.database.create(
            user=True,
            academy=True,
            credentials_github=True,
            credentials_github_kwargs={"username": "from-creds"},
            github_academy_user=True,
            github_academy_user_kwargs={"username": "legacy-slug"},
        )
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        self.assertEqual(resolve_github_username(gau), "from-creds")


class CopilotGrantRevokeTestSuite(AuthTestCase):
    @patch("breathecode.authenticate.actions.Github")
    def test_grant_copilot_seat_for_user_calls_api(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client

        models = self.bc.database.create(
            user=True,
            academy=True,
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "carl"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "my-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )

        grant_copilot_seat_for_user(models.github_academy_user.id)
        mock_client.copilot_add_selected_users.assert_called_once_with(["carl"])

    @patch("breathecode.authenticate.actions.Github")
    def test_revoke_skipped_when_sibling_still_eligible(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client

        models = self.bc.database.create(
            academy=True,
            user=True,
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "dana"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "shared-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        set_copilot_mode(models.academy, "all")
        models2 = self.bc.database.create(academy=True)
        set_copilot_mode(models2.academy, "all")
        self.bc.database.create(
            academy=models2.academy,
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "shared-org"},
        )
        GithubAcademyUser.objects.create(
            academy=models2.academy,
            user=models.user,
            storage_status="SYNCHED",
            storage_action="ADD",
        )

        gau1 = GithubAcademyUser.objects.get(academy=models.academy.id, user=models.user.id)
        gau1.storage_status = "PENDING"
        gau1.storage_action = "DELETE"
        gau1.save()

        revoke_copilot_seat_after_delay(gau1.id)
        mock_client.copilot_remove_selected_users.assert_not_called()

    @patch("breathecode.authenticate.actions.Github")
    def test_revoke_calls_api_when_no_sibling(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client

        models = self.bc.database.create(
            user=True,
            academy=True,
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "erin"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "solo-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "DELETE"},
        )
        revoke_copilot_seat_after_delay(models.github_academy_user.id)
        mock_client.copilot_remove_selected_users.assert_called_once_with(["erin"])


class CopilotReconcileTestSuite(AuthTestCase):
    @patch("breathecode.authenticate.actions.Github")
    def test_reconcile_removes_seats_not_in_allowed_set(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client
        mock_client.copilot_list_billing_seats.return_value = [
            {"assignee": {"login": "allowed-user"}},
            {"assignee": {"login": "stranger"}},
        ]

        models = self.bc.database.create(
            user=True,
            academy=True,
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "allowed-user"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "bill-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        set_copilot_mode(models.academy, "all")

        stats = reconcile_copilot_seats_for_org("bill-org")
        self.assertEqual(stats["org"], "bill-org")
        self.assertIn("stranger", stats["removed_usernames"])
        self.assertEqual(stats["added_usernames"], [])
        mock_client.copilot_remove_selected_users.assert_called_once()
        args, _kwargs = mock_client.copilot_remove_selected_users.call_args
        self.assertEqual(set(args[0]), {"stranger"})
        mock_client.copilot_add_selected_users.assert_not_called()

    @patch("breathecode.authenticate.actions.Github")
    def test_reconcile_adds_missing_seats_for_allowed_users(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client
        mock_client.copilot_list_billing_seats.return_value = []

        models = self.bc.database.create(
            user=True,
            academy=True,
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "needs-seat"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "grant-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        set_copilot_mode(models.academy, "all")

        stats = reconcile_copilot_seats_for_org("grant-org")
        self.assertEqual(stats["added_usernames"], ["needs-seat"])
        mock_client.copilot_add_selected_users.assert_called_once_with(["needs-seat"])
        mock_client.copilot_remove_selected_users.assert_not_called()

    @patch("breathecode.authenticate.actions.Github")
    def test_reconcile_skips_org_without_auto_mode_academies(self, mock_gh_cls):
        mock_client = MagicMock()
        mock_gh_cls.return_value = mock_client
        mock_client.copilot_list_billing_seats.return_value = []

        self.bc.database.create(
            user=True,
            academy=True,
            academy_kwargs={"academy_features": {"commerce": {"copilot_provisioning": "selective"}}},
            credentials_github=True,
            credentials_github_kwargs={"token": "pat", "username": "ignored-user"},
            academy_auth_settings=True,
            academy_auth_settings_kwargs={"github_username": "selective-org"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )

        stats = reconcile_copilot_seats_for_org("selective-org")
        self.assertTrue(stats["skipped"])
        self.assertEqual(stats["reason"], "no_token")
        mock_client.copilot_add_selected_users.assert_not_called()
        mock_client.copilot_remove_selected_users.assert_not_called()


class CopilotGithubAcademyUserReceiverTestSuite(AuthTestCase):
    @patch("breathecode.authenticate.receivers.academy_allows_auto_copilot_by_id", return_value=True)
    @patch("breathecode.authenticate.tasks.revoke_github_copilot_seat_delayed.apply_async")
    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_receiver_schedules_grant_on_synched_add(self, mock_grant_delay, mock_revoke_async, _mock_auto):
        models = self.bc.database.create(
            user=True,
            academy=True,
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "ADD"},
        )
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        gau._copilot_prev_storage_status = "PENDING"
        gau._copilot_prev_storage_action = "ADD"
        gau.storage_status = "SYNCHED"
        github_academy_user_copilot_schedule(
            sender=GithubAcademyUser,
            instance=gau,
            created=False,
            update_fields={"storage_status", "storage_action"},
        )
        mock_grant_delay.assert_called_once_with(gau.id)
        mock_revoke_async.assert_not_called()

    @patch("breathecode.authenticate.receivers.academy_allows_auto_copilot_by_id", return_value=True)
    @patch("breathecode.authenticate.tasks.revoke_github_copilot_seat_delayed.apply_async")
    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_receiver_schedules_revoke_when_leaving_eligible(self, mock_grant_delay, mock_revoke_async, _mock_auto):
        models = self.bc.database.create(
            user=True,
            academy=True,
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "ADD"},
        )
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        gau._copilot_prev_storage_status = "PENDING"
        gau._copilot_prev_storage_action = "ADD"
        gau.storage_status = "SYNCHED"
        github_academy_user_copilot_schedule(
            sender=GithubAcademyUser,
            instance=gau,
            created=False,
            update_fields={"storage_status", "storage_action"},
        )
        mock_grant_delay.assert_called_once_with(gau.id)
        mock_grant_delay.reset_mock()
        mock_revoke_async.reset_mock()
        gau._copilot_prev_storage_status = "SYNCHED"
        gau._copilot_prev_storage_action = "ADD"
        gau.storage_status = "PENDING"
        gau.storage_action = "DELETE"
        github_academy_user_copilot_schedule(
            sender=GithubAcademyUser,
            instance=gau,
            created=False,
            update_fields={"storage_status", "storage_action"},
        )
        mock_revoke_async.assert_called_once()
        self.assertEqual(mock_revoke_async.call_args.kwargs["countdown"], COPILOT_REVOKE_DELAY_SECONDS)
        mock_grant_delay.assert_not_called()

    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_receiver_skips_copilot_when_only_storage_log_updated(self, mock_grant_delay):
        models = self.bc.database.create(
            user=True,
            academy=True,
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        mock_grant_delay.reset_mock()
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        gau.log("noise")
        gau.save(update_fields=["storage_log", "updated_at"])
        mock_grant_delay.assert_not_called()

    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_receiver_skips_grant_for_selective_mode(self, mock_grant_delay):
        models = self.bc.database.create(
            user=True,
            academy=True,
            academy_kwargs={"academy_features": {"commerce": {"copilot_provisioning": "selective"}}},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "ADD"},
        )
        gau = GithubAcademyUser.objects.get(id=models.github_academy_user.id)
        gau.storage_status = "SYNCHED"
        gau.save()
        gau.refresh_from_db()
        mock_grant_delay.assert_not_called()
        self.assertIn("auto-grant skipped", (gau.storage_log or [])[-1]["msg"])


class CopilotBatchScheduleTestSuite(AuthTestCase):
    @patch("breathecode.authenticate.tasks.grant_github_copilot_seat_task.delay")
    def test_schedule_copilot_grants_for_academy_users_returns_scheduled_and_skipped(self, mock_delay):
        models = self.bc.database.create(
            academy=True,
            user=True,
            credentials_github=True,
            credentials_github_kwargs={"username": "eligible-user"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "SYNCHED", "storage_action": "ADD"},
        )
        models2 = self.bc.database.create(
            academy=models.academy.id,
            user=True,
            credentials_github=True,
            credentials_github_kwargs={"username": "not-ready"},
            github_academy_user=True,
            github_academy_user_kwargs={"storage_status": "PENDING", "storage_action": "ADD"},
        )

        result = schedule_copilot_grants_for_academy_users(models.academy.id, [models.user.id, models2.user.id, 9999])

        self.assertEqual(result["total_requested"], 3)
        self.assertEqual(len(result["scheduled"]), 1)
        self.assertEqual(result["scheduled"][0]["user_id"], models.user.id)
        self.assertEqual(len(result["skipped"]), 2)
        self.assertEqual(mock_delay.call_count, 1)


class GithubServiceCopilotDeleteTest(TestCase):
    @patch("breathecode.services.github.requests.request")
    def test_delete_with_json_body_parses_response(self, mock_request):
        from breathecode.services.github import Github

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"seats_cancelled":1}'
        mock_resp.json.return_value = {"seats_cancelled": 1}
        mock_request.return_value = mock_resp

        gh = Github(token="t", org="o")
        data = gh.delete("/orgs/o/copilot/billing/selected_users", json={"selected_usernames": ["u"]})
        self.assertEqual(data, {"seats_cancelled": 1})
        mock_request.assert_called_once()
        _args, kwargs = mock_request.call_args
        method = _args[0] if _args else kwargs.get("method")
        self.assertEqual(method, "DELETE")
        self.assertEqual(kwargs["json"], {"selected_usernames": ["u"]})
