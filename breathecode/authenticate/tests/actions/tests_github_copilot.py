"""Tests for GitHub Copilot provisioning, deprovision, storage_log, and deferred revoke."""

from unittest.mock import MagicMock, patch

from breathecode.authenticate.actions import (
    _append_copilot_storage_log,
    deferred_github_copilot_remove_if_still_revoked,
    deprovision_github_copilot_for_user,
    provision_github_copilot_for_user,
)
from breathecode.authenticate.models import ADD, SYNCHED, GithubAcademyUser

from ..mixins.new_auth_test_case import AuthTestCase


class CopilotAppendStorageLogTest(AuthTestCase):
    def test_append_copilot_storage_log_uses_sibling_academy_ids_to_find_row(self):
        """Log must attach to a GHAU row in sibling_academy_ids when academy_id alone has no row."""
        models = self.bc.database.create(
            user=True,
            academy=2,
            credentials_github=True,
            academy_auth_settings={"github_username": "shared-org"},
            github_academy_user={"storage_status": SYNCHED, "storage_action": ADD},
        )
        user = models.user
        academies = models.academy if isinstance(models.academy, list) else [models.academy]
        a0_id = academies[0].id
        a1_id = academies[1].id

        ghu = GithubAcademyUser.objects.get(user=user)
        ghu.academy_id = a1_id
        ghu.save(update_fields=["academy_id"])

        _append_copilot_storage_log(user.id, a0_id, "only-academy-id-no-row")
        ghu.refresh_from_db()
        self.assertFalse(any("only-academy-id-no-row" in (e.get("msg") or "") for e in (ghu.storage_log or [])))

        _append_copilot_storage_log(
            user.id,
            a0_id,
            "with-sibling-ids",
            sibling_academy_ids=[a0_id, a1_id],
        )
        ghu.refresh_from_db()
        self.assertTrue(any("with-sibling-ids" in (e.get("msg") or "") for e in (ghu.storage_log or [])))


class CopilotDeferredRevokeTest(AuthTestCase):
    @patch("breathecode.authenticate.actions.github_academy_user_allows_copilot_in_sibling_academies", return_value=True)
    @patch("breathecode.authenticate.actions.deprovision_github_copilot_for_user")
    def test_deferred_skips_when_sibling_still_synched_add(self, mock_deprov, _mock_sibling):
        models = self.bc.database.create(user=True, academy=True)
        deferred_github_copilot_remove_if_still_revoked(models.user.id, models.academy.id)
        mock_deprov.assert_not_called()

    @patch("breathecode.authenticate.actions.github_academy_user_allows_copilot_in_sibling_academies", return_value=False)
    @patch("breathecode.authenticate.actions._user_has_copilot_entitlement", return_value=True)
    @patch("breathecode.authenticate.actions._get_copilot_client_for_user")
    def test_deferred_skips_when_global_copilot_consumable_remains(self, mock_client, _mock_ent, _mock_sibling):
        models = self.bc.database.create(user=True, academy=True)
        out = deferred_github_copilot_remove_if_still_revoked(models.user.id, models.academy.id)
        self.assertFalse(out)
        mock_client.assert_not_called()

    @patch("breathecode.authenticate.actions.github_academy_user_allows_copilot_in_sibling_academies", return_value=False)
    @patch("breathecode.authenticate.actions._user_has_copilot_entitlement", return_value=False)
    @patch("breathecode.authenticate.actions._get_copilot_client_for_user")
    def test_deferred_removes_when_no_sibling_add_and_no_consumable(self, mock_get_client, _mock_ent, _mock_sibling):
        gh = MagicMock()
        gh.org = "test-org"
        gh.copilot_remove_selected_users = MagicMock(return_value={"ok": True})
        mock_get_client.return_value = (gh, "ghuser")
        models = self.bc.database.create(user=True, academy=True, credentials_github=True)
        out = deferred_github_copilot_remove_if_still_revoked(models.user.id, models.academy.id)
        self.assertTrue(out)
        gh.copilot_remove_selected_users.assert_called_once()


class CopilotDeprovisionTest(AuthTestCase):
    @patch("breathecode.authenticate.actions._user_has_copilot_entitlement", return_value=True)
    @patch("breathecode.authenticate.actions._get_copilot_client_for_user")
    def test_deprovision_skips_when_any_active_consumable(self, mock_client, _mock_ent):
        models = self.bc.database.create(user=True, academy=True)
        ok = deprovision_github_copilot_for_user(models.user.id, academy_id=models.academy.id)
        self.assertFalse(ok)
        mock_client.assert_not_called()


class CopilotProvisionTest(AuthTestCase):
    @patch("breathecode.authenticate.actions._get_copilot_client_for_user")
    @patch("breathecode.authenticate.actions._copilot_entitlement_ok_for_provision", return_value=True)
    @patch("breathecode.authenticate.actions.github_academy_user_allows_copilot_in_sibling_academies", return_value=True)
    def test_provision_sibling_writes_storage_log_on_ghau_row(self, mock_sibling, mock_ent, mock_get_client):
        models = self.bc.database.create(
            user=True,
            academy=2,
            credentials_github=True,
            academy_auth_settings={"github_username": "org-slug"},
            github_academy_user={"storage_status": SYNCHED, "storage_action": ADD},
        )
        user = models.user
        academies = models.academy if isinstance(models.academy, list) else [models.academy]
        a0_id = academies[0].id
        a1_id = academies[1].id
        ghu = GithubAcademyUser.objects.get(user=user)
        ghu.academy_id = a1_id
        ghu.save(update_fields=["academy_id"])

        gh = MagicMock()
        gh.org = "org-slug"
        gh.copilot_add_selected_users = MagicMock(return_value={"ok": True})
        mock_get_client.return_value = (gh, "loginuser")

        ok = provision_github_copilot_for_user(
            user.id,
            academy_id=a0_id,
            sibling_academy_ids=[a0_id, a1_id],
            source="reconcile_github_copilot_seats",
        )
        self.assertTrue(ok)
        gh.copilot_add_selected_users.assert_called_once()
        ghu.refresh_from_db()
        self.assertTrue(
            any("Copilot add done" in (e.get("msg") or "") for e in (ghu.storage_log or [])),
            msg=ghu.storage_log,
        )
        self.assertTrue(
            any("reconcile_github_copilot_seats" in (e.get("msg") or "") for e in (ghu.storage_log or [])),
            msg=ghu.storage_log,
        )
