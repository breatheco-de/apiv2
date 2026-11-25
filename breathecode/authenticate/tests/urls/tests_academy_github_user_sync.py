"""PUT /v1/auth/academy/github/user/sync with user_id (sync of a single user)."""

from unittest.mock import patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.authenticate.models import AcademyAuthSettings, CredentialsGithub, GithubAcademyUser

from ..mixins.new_auth_test_case import AuthTestCase


class SyncGithubUserTestSuite(AuthTestCase):
    def setUp(self):
        super().setUp()
        model = self.bc.database.create(user=2, profile_academy=1, role=1, capability="sync_organization_users")
        self.staff, self.student = model.user
        self.academy_id = model.profile_academy.academy_id
        for user, github_id in ((self.staff, 1), (self.student, 2)):
            CredentialsGithub.objects.create(
                github_id=github_id, user=user, token="t", email=f"u{github_id}@example.com", username=f"gh-{github_id}"
            )
        AcademyAuthSettings.objects.create(
            academy_id=self.academy_id, github_username="org", github_owner=self.staff, github_is_sync=True
        )
        self.client.force_authenticate(self.staff)
        self.headers(academy=self.academy_id)
        self.url = reverse_lazy("authenticate:github_user_sync")

    def _row(self, storage_status, storage_action):
        GithubAcademyUser.objects.all().delete()
        GithubAcademyUser.objects.bulk_create(
            [
                GithubAcademyUser(
                    academy_id=self.academy_id,
                    user=self.student,
                    storage_status=storage_status,
                    storage_action=storage_action,
                )
            ]
        )

    def _put(self, user_id):
        return self.client.put(self.url, {"user_id": user_id}, format="json")

    @patch("breathecode.authenticate.views.sync_organization_members")
    def test_nothing_is_synched(self, sync):
        self.assertEqual(self._put(self.student.id).status_code, status.HTTP_404_NOT_FOUND)
        for user_id in (None, "", "abc"):
            self.assertEqual(self._put(user_id).status_code, status.HTTP_400_BAD_REQUEST)

        for row in (("PENDING", "DELETE"), ("SYNCHED", "IGNORE")):
            self._row(*row)
            response = self._put(self.student.id)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["detail"], "github-user-action-not-allowed")

        self._row("SYNCHED", "ADD")
        response = self._put(self.student.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["storage_status"], "SYNCHED")
        sync.assert_not_called()

    @patch("breathecode.authenticate.actions.Github")
    def test_sync_returns_the_updated_row(self, github):
        github.return_value.get_org_members.return_value = [{"login": "gh-2"}]
        for row in (("SYNCHED", "INVITE"), ("ERROR", "ADD"), ("PENDING", "ADD")):
            self._row(*row)
            data = self._put(self.student.id).json()
            self.assertEqual((data["storage_status"], data["storage_action"]), ("SYNCHED", "ADD"), row)

        github.return_value.get_org_members.return_value = []
        self._row("PENDING", "ADD")
        data = self._put(self.student.id).json()
        self.assertEqual((data["storage_status"], data["storage_action"]), ("SYNCHED", "INVITE"))
        github.return_value.delete_org_member.assert_not_called()

    @patch("breathecode.authenticate.views.sync_organization_members", return_value=True)
    def test_without_user_id_syncs_the_academy(self, sync):
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sync.assert_called_once_with(self.academy_id)
