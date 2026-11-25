"""
GitHub Copilot as a ProvisioningAcademy (vendor "copilot", type CODING_ASSISTANT):
- POST/PUT /v1/provisioning/academy/provisioningacademy validation and credentials_set
- POST /v1/provisioning/academy/provisioningacademy/<id>/test-connection
- GET/POST /v1/provisioning/academy/copilot and GET /v1/provisioning/me/copilot
"""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.authenticate.models import ADD, SYNCHED, CredentialsGithub, GithubAcademyUser
from breathecode.provisioning.models import (
    COPILOT_VENDOR_NAME,
    ProvisioningAcademy,
    ProvisioningCopilot,
    ProvisioningVendor,
)

from ..mixins import ProvisioningTestCase


def _copilot_vendor():
    vendor, _ = ProvisioningVendor.objects.get_or_create(
        name=COPILOT_VENDOR_NAME,
        defaults={
            "vendor_type": ProvisioningVendor.VendorType.CODING_ASSISTANT,
            "workspaces_url": "https://github.com",
        },
    )
    return vendor


def _creds(user, *, github_id, token="", username=None):
    return CredentialsGithub.objects.create(
        github_id=github_id, user=user, token=token, email=f"u{github_id}@example.com", username=username
    )


class CopilotProvisioningAcademyTestSuite(ProvisioningTestCase):
    def _staff(self, capability="crud_provisioning_activity"):
        model = self.bc.database.create(user=1, profile_academy=1, role=1, capability=capability)
        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        return model

    def test_post_create_with_owner_user_and_no_token(self):
        model = self._staff()
        _creds(model.user, github_id=1, token="owner-token")
        vendor = _copilot_vendor()
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.post(
            url,
            data={
                "vendor_id": vendor.id,
                "vendor_settings": {
                    "org": "  my-org ",
                    "github_owner_user_id": model.user.id,
                    "allow_auto_provision": False,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        data = response.json()
        self.assertTrue(data["credentials_set"])
        self.assertEqual(
            data["vendor_settings"],
            {"org": "my-org", "github_owner_user_id": model.user.id, "allow_auto_provision": False},
        )

    def test_post_create_without_token_nor_owner_fails(self):
        self._staff()
        vendor = _copilot_vendor()
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.post(
            url, data={"vendor_id": vendor.id, "vendor_settings": {"org": "my-org"}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "missing-copilot-credentials")
        self.assertEqual(ProvisioningAcademy.objects.count(), 0)

    def test_post_create_validates_copilot_vendor_settings(self):
        self._staff()
        vendor = _copilot_vendor()
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        cases = [
            ({}, "missing-copilot-org"),
            ({"org": "o", "unknown": 1}, "invalid-vendor-settings-keys"),
            ({"org": "o", "allow_auto_provision": "no"}, "invalid-vendor-settings-value"),
            ({"org": "o", "github_owner_user_id": "abc"}, "invalid-vendor-settings-value"),
            ({"org": "o", "github_owner_user_id": 999999}, "copilot-owner-github-not-connected"),
        ]
        for vendor_settings, slug in cases:
            response = self.client.post(
                url,
                data={"vendor_id": vendor.id, "credentials_token": "t", "vendor_settings": vendor_settings},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, vendor_settings)
            self.assertEqual(response.json()["detail"], slug, vendor_settings)

    def test_post_create_other_vendors_still_require_token(self):
        self._staff()
        vendor = ProvisioningVendor.objects.create(
            name="hostinger",
            vendor_type=ProvisioningVendor.VendorType.VPS_SERVER,
            workspaces_url="https://hostinger.example.com",
        )
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.post(url, data={"vendor_id": vendor.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ProvisioningAcademy.objects.count(), 0)

    def test_put_cannot_leave_copilot_pa_without_credentials(self):
        model = self._staff()
        pa = ProvisioningAcademy.objects.create(
            academy_id=model.profile_academy.academy_id,
            vendor=_copilot_vendor(),
            credentials_token="tok",
            vendor_settings={"org": "my-org"},
        )
        url = reverse_lazy("provisioning:academy_provisioning_academy_id", kwargs={"provisioning_academy_id": pa.id})
        response = self.client.put(url, data={"credentials_token": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "missing-copilot-credentials")
        pa.refresh_from_db()
        self.assertEqual(pa.credentials_token, "tok")

    def test_put_cannot_clear_the_token_of_other_vendors(self):
        model = self._staff()
        vendor = ProvisioningVendor.objects.create(name="litellm", vendor_type="LLM")
        pa = ProvisioningAcademy.objects.create(
            academy_id=model.profile_academy.academy_id, vendor=vendor, credentials_token="tok"
        )
        url = reverse_lazy("provisioning:academy_provisioning_academy_id", kwargs={"provisioning_academy_id": pa.id})
        response = self.client.put(url, data={"credentials_token": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.provisioning.views.Github")
    def test_test_connection_success(self, github_cls):
        model = self._staff()
        github_cls.return_value.copilot_billing_summary.return_value = {"seat_breakdown": {"total": 1}}
        pa = ProvisioningAcademy.objects.create(
            academy_id=model.profile_academy.academy_id,
            vendor=_copilot_vendor(),
            credentials_token="tok",
            vendor_settings={"org": "my-org"},
        )
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection", kwargs={"provisioning_academy_id": pa.id}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)
        github_cls.assert_called_once_with(org="my-org", token="tok")

    def test_test_connection_error_when_owner_has_no_token(self):
        model = self._staff()
        pa = ProvisioningAcademy.objects.create(
            academy_id=model.profile_academy.academy_id,
            vendor=_copilot_vendor(),
            vendor_settings={"org": "my-org", "github_owner_user_id": model.user.id},
        )
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection", kwargs={"provisioning_academy_id": pa.id}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.ERROR)


class AcademyCopilotTestSuite(ProvisioningTestCase):
    def setUp(self):
        super().setUp()
        model = self.bc.database.create(user=2, profile_academy=1, role=1, capability="crud_provisioning_activity")
        self.staff, self.student = model.user
        self.academy_id = model.profile_academy.academy_id
        self.other_academy = self.bc.database.create(academy=1).academy
        for academy_id in (self.academy_id, self.other_academy.id):
            ProvisioningAcademy.objects.create(
                academy_id=academy_id,
                vendor=_copilot_vendor(),
                credentials_token="tok",
                vendor_settings={"org": "my-org", "allow_auto_provision": False},
            )
        _creds(self.student, github_id=50, username="student-gh")
        GithubAcademyUser.objects.bulk_create(
            [
                GithubAcademyUser(
                    academy_id=self.academy_id, user=self.student, storage_status=SYNCHED, storage_action=ADD
                )
            ]
        )
        self.client.force_authenticate(self.staff)
        self.headers(academy=self.academy_id)
        self.url = reverse_lazy("provisioning:academy_copilot")

    def _post(self, *entitled_ids, gh=None, body=None):
        def has_entitlement(user, academy_id=None):
            return academy_id in entitled_ids

        with (
            patch("breathecode.authenticate.actions._user_has_copilot_entitlement", side_effect=has_entitlement),
            patch("breathecode.provisioning.views._user_has_copilot_entitlement", side_effect=has_entitlement),
            patch("breathecode.authenticate.actions.Github", return_value=gh or MagicMock(org="my-org")),
        ):
            return self.client.post(self.url, data=body or {"user_id": self.student.id}, format="json")

    def _assert_error(self, response, slug):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], slug)

    def test_requires_capability(self):
        self.staff.profileacademy_set.first().role.capabilities.clear()
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._post(self.academy_id).status_code, status.HTTP_403_FORBIDDEN)

    def test_post_assigns_seat_in_manual_mode(self):
        gh = MagicMock(org="my-org")
        gh.copilot_add_selected_users.return_value = {"seats_created": 1}
        response = self._post(self.academy_id, gh=gh)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual((response.json()["user"]["id"], response.json()["status"]), (self.student.id, "ACTIVE"))
        gh.copilot_add_selected_users.assert_called_once_with(["student-gh"])

    def test_post_errors(self):
        # a consumable in a sibling academy isn't enough
        self._assert_error(self._post(self.other_academy.id), "no-copilot-entitlement")

        gh = MagicMock(org="my-org")
        gh.copilot_add_selected_users.side_effect = Exception("boom")
        self._assert_error(self._post(self.academy_id, gh=gh), "copilot-provision-failed")

        GithubAcademyUser.objects.all().delete()
        self._assert_error(self._post(self.academy_id), "github-not-synched")

        CredentialsGithub.objects.filter(user=self.student).delete()
        self._assert_error(self._post(self.academy_id), "github-not-connected")

        ProvisioningAcademy.objects.update(credentials_token="")
        self._assert_error(self._post(self.academy_id), "copilot-not-configured")

        self.assertEqual(self._post(body={"user_id": "abc"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._post(body={"user_id": 999999}).status_code, status.HTTP_404_NOT_FOUND)

    def test_get_lists(self):
        for user, academy_id, seat_status in (
            (self.student, self.academy_id, "ACTIVE"),
            (self.staff, self.academy_id, "PENDING"),
            (self.student, self.other_academy.id, "ACTIVE"),
        ):
            ProvisioningCopilot.objects.create(user=user, academy_id=academy_id, org="my-org", status=seat_status)

        def users(query=""):
            return sorted(row["user"]["id"] for row in self.client.get(f"{self.url}{query}").json())

        self.assertEqual(users(), sorted([self.staff.id, self.student.id]))  # only this academy
        self.assertEqual(users("?status=active"), [self.student.id])
        self.assertEqual(users(f"?user_id={self.staff.id}"), [self.staff.id])

        response = self.client.get(reverse_lazy("provisioning:me_copilot"))
        self.assertEqual([row["user"]["id"] for row in response.json()], [self.staff.id])  # only own rows

    def test_get_org(self):
        ProvisioningAcademy.objects.filter(academy_id=self.other_academy.id).update(vendor_settings={"org": "MY-ORG"})
        url = reverse_lazy("provisioning:academy_copilot_org")
        data = self.client.get(url).json()
        self.assertEqual(data["org"], "my-org")
        self.assertEqual(
            {academy["id"]: academy["allow_auto_provision"] for academy in data["academies"]},
            {self.academy_id: False, self.other_academy.id: True},
        )

        ProvisioningAcademy.objects.all().delete()
        self.assertEqual(self.client.get(url).json(), {"org": None, "academies": []})
