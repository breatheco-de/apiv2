"""Tests for GitHub Copilot provisioning, deprovision, storage_log, and deferred revoke."""

from unittest.mock import MagicMock, patch

from breathecode.authenticate.actions import (
    _append_copilot_storage_log,
    copilot_org_sibling_academy_ids,
    deferred_github_copilot_remove_if_still_revoked,
    deprovision_github_copilot_for_user,
    get_copilot_settings,
    is_copilot_auto_provision_enabled,
    provision_github_copilot_for_user,
    save_provisioning_copilot_status,
)
from breathecode.authenticate.models import (
    ADD,
    SYNCHED,
    AcademyAuthSettings,
    CredentialsGithub,
    GithubAcademyUser,
)
from breathecode.authenticate.receivers import (
    github_academy_user_copilot_react,
    provision_github_copilot_on_service_granted,
)
from breathecode.payments.models import Consumable, Service, ServiceItem, Subscription
from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningCopilot, ProvisioningVendor

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


# ---------------------------------------------------------------------------
# Copilot as a ProvisioningAcademy
# ---------------------------------------------------------------------------

ACTIONS = "breathecode.authenticate.actions"


class CopilotTestCase(AuthTestCase):
    """Two academies and a student; entitlement is mocked by academy id."""

    def setUp(self):
        super().setUp()
        models = self.bc.database.create(academy=2, user=2)
        self.a0, self.a1 = models.academy
        self.owner, self.student = models.user
        self._creds(self.owner, 1, token="owner-token")
        self._creds(self.student, 2, username="student-gh")

    def _creds(self, user, github_id, token="", username=None):
        CredentialsGithub.objects.create(
            github_id=github_id, user=user, token=token, email=f"u{github_id}@example.com", username=username
        )

    def _pa(self, academy, token="", **vendor_settings):
        vendor, _ = ProvisioningVendor.objects.get_or_create(
            name="Copilot", defaults={"vendor_type": "CODING_ASSISTANT", "workspaces_url": "https://github.com"}
        )
        return ProvisioningAcademy.objects.create(
            academy=academy, vendor=vendor, credentials_token=token, vendor_settings=vendor_settings
        )

    def _auth_settings(self, academy, org):
        AcademyAuthSettings.objects.create(academy=academy, github_username=org, github_owner=self.owner)

    def _entitled(self, *academies):
        ids = {academy.id for academy in academies}
        return patch(
            f"{ACTIONS}._user_has_copilot_entitlement",
            side_effect=lambda user, academy_id=None: bool(ids) if academy_id is None else academy_id in ids,
        )

    def _rows(self):
        return {
            row.academy_id: (row.status, row.status_text) for row in ProvisioningCopilot.objects.filter(user=self.student)
        }


class CopilotSettingsTest(CopilotTestCase):
    def test_without_pa_uses_auth_settings(self):
        self._auth_settings(self.a0, "legacy-org")
        self.assertEqual(get_copilot_settings(self.a0.id), (self.a0.id, "legacy-org", "owner-token"))

    def test_pa_token_wins_over_owner_and_auth_settings(self):
        self._auth_settings(self.a0, "legacy-org")
        self._pa(self.a0, token="pa-token", org="pa-org", github_owner_user_id=self.owner.id)
        self.assertEqual(get_copilot_settings(self.a0.id), (self.a0.id, "pa-org", "pa-token"))

    def test_pa_owner_token(self):
        self._pa(self.a0, org="pa-org", github_owner_user_id=self.owner.id)
        self.assertEqual(get_copilot_settings(self.a0.id), (self.a0.id, "pa-org", "owner-token"))

    def test_incomplete_pa_does_not_fall_back(self):
        self._auth_settings(self.a0, "legacy-org")
        self._pa(self.a0, org="pa-org")
        self.assertEqual(get_copilot_settings(self.a0.id), (self.a0.id, "pa-org", None))

    def test_none_academy_uses_first_auth_settings(self):
        self._auth_settings(self.a0, "first-org")
        self._auth_settings(self.a1, "second-org")
        self.assertEqual(get_copilot_settings(None), (self.a0.id, "first-org", "owner-token"))

    def test_siblings_pa_always_wins_over_auth_settings(self):
        self._auth_settings(self.a0, "Shared")
        self._auth_settings(self.a1, "shared")
        self.assertEqual(copilot_org_sibling_academy_ids("shared"), [self.a0.id, self.a1.id])
        self._pa(self.a1, token="t", org="other")
        self.assertEqual(copilot_org_sibling_academy_ids("shared"), [self.a0.id])


class CopilotAutoProvisionTest(CopilotTestCase):
    def test_automatic_without_pa_or_without_key(self):
        self._auth_settings(self.a0, "org")
        self._pa(self.a1, token="t", org="org")
        with self._entitled(self.a0, self.a1):
            self.assertTrue(is_copilot_auto_provision_enabled(self.student, self.a0.id))

    def test_manual_wins_only_where_the_user_is_entitled(self):
        self._auth_settings(self.a0, "org")
        self._pa(self.a1, token="t", org="org", allow_auto_provision=False)
        with self._entitled(self.a0, self.a1):
            self.assertFalse(is_copilot_auto_provision_enabled(self.student, self.a0.id))
        with self._entitled(self.a0):
            self.assertTrue(is_copilot_auto_provision_enabled(self.student, self.a0.id))

    def test_unsaved_consumable_counts(self):
        self._pa(self.a0, token="t", org="org", allow_auto_provision=False)
        with self._entitled():
            self.assertFalse(
                is_copilot_auto_provision_enabled(self.student, self.a0.id, consumable_academy_id=self.a0.id)
            )


class ProvisioningCopilotTest(CopilotTestCase):
    def setUp(self):
        super().setUp()
        for academy in (self.a0, self.a1):
            self._pa(academy, token="t", org="org", allow_auto_provision=False)
        self.gh = MagicMock(org="org")
        github = patch(f"{ACTIONS}.Github", return_value=self.gh)
        github.start()
        self.addCleanup(github.stop)
        GithubAcademyUser.objects.bulk_create(
            [GithubAcademyUser(academy=self.a0, user=self.student, storage_status=SYNCHED, storage_action=ADD)]
        )

    def test_provision_and_deprovision_share_status_between_siblings(self):
        with self._entitled(self.a0, self.a1):
            self.assertTrue(provision_github_copilot_for_user(self.student.id, self.a0.id))
        self.gh.copilot_add_selected_users.assert_called_once_with(["student-gh"])
        self.assertEqual(self._rows(), {self.a0.id: ("ACTIVE", ""), self.a1.id: ("ACTIVE", "")})

        with self._entitled():
            self.assertTrue(deprovision_github_copilot_for_user(self.student.id, self.a0.id))
        self.assertEqual(self._rows(), {self.a0.id: ("DEPROVISIONED", ""), self.a1.id: ("DEPROVISIONED", "")})

    def test_missing_membership_is_pending(self):
        GithubAcademyUser.objects.all().delete()
        with self._entitled(self.a0):
            self.assertFalse(provision_github_copilot_for_user(self.student.id, self.a0.id))
        self.assertEqual(self._rows(), {self.a0.id: ("PENDING", "github-not-synched")})

    def test_github_error(self):
        self.gh.copilot_add_selected_users.side_effect = Exception("boom")
        with self._entitled(self.a0):
            self.assertFalse(provision_github_copilot_for_user(self.student.id, self.a0.id))
            with self.assertRaisesMessage(Exception, "boom"):
                provision_github_copilot_for_user(self.student.id, self.a0.id, raise_exception=True)
        self.assertEqual(self._rows(), {self.a0.id: ("ERROR", "boom")})

    def test_active_is_kept_and_inherited_by_new_rows(self):
        with self._entitled(self.a0):
            save_provisioning_copilot_status(self.student, self.a0.id, "ACTIVE")
            save_provisioning_copilot_status(self.student, self.a0.id, "ERROR", "boom")
        self.assertEqual(self._rows(), {self.a0.id: ("ACTIVE", "boom")})
        with self._entitled(self.a0, self.a1):
            save_provisioning_copilot_status(self.student, self.a1.id, "PENDING", "manual-mode")
        self.assertEqual(self._rows(), {self.a0.id: ("ACTIVE", ""), self.a1.id: ("ACTIVE", "")})

    def test_table_failure_does_not_break_the_assignment(self):
        with self._entitled(self.a0), patch(f"{ACTIONS}.copilot_org_sibling_academy_ids", side_effect=Exception("db")):
            self.assertTrue(provision_github_copilot_for_user(self.student.id, self.a0.id))
        self.assertEqual(self._rows(), {})

    @patch("breathecode.authenticate.receivers.tasks")
    def test_receivers_do_not_enqueue_in_manual_mode(self, tasks):
        consumable = Consumable(
            user=self.student,
            subscription=Subscription(academy=self.a0),
            service_item=ServiceItem(service=Service(consumer=Service.Consumer.GITHUB_COPILOT)),
        )
        with self._entitled():  # the consumable isn't saved yet
            provision_github_copilot_on_service_granted(sender=Consumable, instance=consumable)
        self.assertEqual(self._rows(), {self.a0.id: ("PENDING", "manual-mode")})

        with self._entitled(self.a0, self.a1):
            github_academy_user = GithubAcademyUser.objects.get(user=self.student)
            github_academy_user_copilot_react(GithubAcademyUser, github_academy_user, created=True)
        self.assertEqual(
            self._rows(), {self.a0.id: ("PENDING", "manual-mode"), self.a1.id: ("PENDING", "manual-mode")}
        )
        tasks.provision_github_copilot_task.delay.assert_not_called()

        ProvisioningAcademy.objects.update(vendor_settings={"org": "org"})
        with self._entitled(self.a0):
            provision_github_copilot_on_service_granted(sender=Consumable, instance=consumable)
        tasks.provision_github_copilot_task.delay.assert_called_once_with(self.student.id, academy_id=self.a0.id)
