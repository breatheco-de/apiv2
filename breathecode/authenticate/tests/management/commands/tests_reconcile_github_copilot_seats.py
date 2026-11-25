"""Tests for reconcile_github_copilot_seats with Copilot ProvisioningAcademy configs."""

from unittest.mock import MagicMock, patch

from breathecode.authenticate.management.commands.reconcile_github_copilot_seats import (
    run_reconcile_github_copilot_seats,
)
from breathecode.authenticate.models import ADD, SYNCHED, AcademyAuthSettings, CredentialsGithub, GithubAcademyUser
from breathecode.provisioning.models import (
    COPILOT_VENDOR_NAME,
    ProvisioningAcademy,
    ProvisioningCopilot,
    ProvisioningVendor,
)

from ...mixins.new_auth_test_case import AuthTestCase

COMMAND = "breathecode.authenticate.management.commands.reconcile_github_copilot_seats"


def _copilot_pa(academy_id, *, token="", **vendor_settings):
    vendor, _ = ProvisioningVendor.objects.get_or_create(
        name=COPILOT_VENDOR_NAME,
        defaults={
            "vendor_type": ProvisioningVendor.VendorType.CODING_ASSISTANT,
            "workspaces_url": "https://github.com",
        },
    )
    return ProvisioningAcademy.objects.create(
        academy_id=academy_id, vendor=vendor, credentials_token=token, vendor_settings=vendor_settings
    )


def _creds(user, *, github_id, token="", username=None):
    return CredentialsGithub.objects.create(
        github_id=github_id, user=user, token=token, email=f"u{github_id}@example.com", username=username
    )


class ReconcileCopilotSeatsTest(AuthTestCase):
    def setUp(self):
        super().setUp()
        models = self.bc.database.create(academy=1, user=1)
        self.academy = models.academy
        self.student = models.user
        _creds(self.student, github_id=10, username="student-gh")
        # Avoid the GithubAcademyUser post_save receiver queueing real provisioning work.
        with patch("breathecode.authenticate.receivers.tasks"):
            GithubAcademyUser.objects.create(
                academy=self.academy,
                user=self.student,
                username="student-gh",
                storage_status=SYNCHED,
                storage_action=ADD,
            )

    def _run(self, *, seats=None, entitlement_ids=None, dry_run=True):
        gh = MagicMock()
        gh.copilot_list_seat_usernames.return_value = seats or []
        with (
            patch(f"{COMMAND}.Github", return_value=gh) as github_cls,
            patch(f"{COMMAND}._candidate_user_ids_with_copilot_consumable", return_value={self.student.id}),
            patch(
                "breathecode.authenticate.actions._user_has_copilot_entitlement",
                side_effect=lambda user, academy_id=None: academy_id
                in (entitlement_ids if entitlement_ids is not None else {self.academy.id}),
            ),
            patch("breathecode.authenticate.actions.Github", return_value=gh),
        ):
            result = run_reconcile_github_copilot_seats(dry_run=dry_run)
        return result, github_cls, gh

    def test_org_only_in_pa_is_processed_with_pa_credentials(self):
        _copilot_pa(self.academy.id, token="pa-token", org="pa-org")

        result, github_cls, _ = self._run()

        self.assertEqual(result["github_orgs_processed"], 1)
        github_cls.assert_called_once_with(org="pa-org", token="pa-token")
        self.assertEqual([x["user_id"] for x in result["would_add"]], [self.student.id])

    def test_manual_mode_skips_add(self):
        _copilot_pa(self.academy.id, token="pa-token", org="pa-org", allow_auto_provision=False)

        result, _, _ = self._run()

        self.assertEqual(result["would_add"], [])
        self.assertIn(
            {"org": "pa-org", "user_id": self.student.id, "reason": "manual_mode"},
            result["would_skip_add"],
        )

    def test_manual_mode_still_removes_seats_without_entitlement(self):
        _copilot_pa(self.academy.id, token="pa-token", org="pa-org", allow_auto_provision=False)

        result, _, _ = self._run(seats=["student-gh"], entitlement_ids=set())

        self.assertEqual(
            [(x["github_username"], x["reason"]) for x in result["would_remove"]],
            [("student-gh", "student_without_copilot_entitlement")],
        )

    def test_missing_token_is_reported_and_org_skipped(self):
        _copilot_pa(self.academy.id, org="pa-org")

        result, github_cls, _ = self._run()

        github_cls.assert_not_called()
        self.assertEqual(len(result["list_errors"]), 1)
        self.assertEqual(result["list_errors"][0]["org"], "pa-org")

    def test_legacy_auth_settings_still_used_without_pa(self):
        owner = self.bc.database.create(user=1).user
        _creds(owner, github_id=20, token="owner-token")
        AcademyAuthSettings.objects.create(academy=self.academy, github_username="legacy-org", github_owner=owner)

        result, github_cls, _ = self._run()

        github_cls.assert_called_once_with(org="legacy-org", token="owner-token")
        self.assertEqual([x["user_id"] for x in result["would_add"]], [self.student.id])

    def test_pa_without_token_does_not_block_the_org(self):
        _copilot_pa(self.academy.id, org="shared-org")
        other = self.bc.database.create(academy=1, user=1)
        _creds(other.user, github_id=20, token="owner-token")
        AcademyAuthSettings.objects.create(academy=other.academy, github_username="shared-org", github_owner=other.user)

        _, github_cls, _ = self._run()

        github_cls.assert_called_once_with(org="shared-org", token="owner-token")

    def test_table_is_aligned_with_github(self):
        _copilot_pa(self.academy.id, token="pa-token", org="pa-org", allow_auto_provision=False)

        self._run(seats=["student-gh"])
        self.assertEqual(ProvisioningCopilot.objects.count(), 0)  # dry run

        self._run(seats=["student-gh"], dry_run=False)
        row = ProvisioningCopilot.objects.get(user=self.student)
        self.assertEqual((row.status, row.provisioned_at), ("ACTIVE", None))

        self._run(seats=[], dry_run=False)
        row.refresh_from_db()
        self.assertEqual(row.status, "DEPROVISIONED")
        self.assertIsNotNone(row.deprovisioned_at)
