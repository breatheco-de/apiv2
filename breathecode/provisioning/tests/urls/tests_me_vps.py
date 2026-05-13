"""Tests for GET/POST /provisioning/me/vps and GET /provisioning/me/vps/<id>."""

from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningVPS
from breathecode.provisioning.utils.vps_client import VPSProvisioningError

from ..mixins import ProvisioningTestCase


class MeVPSViewTestSuite(ProvisioningTestCase):
    def test_me_vps_get_empty_list(self):
        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"], [])
        self.assertFalse(response.json()["can_request_vps"])

    def test_me_vps_get_list_returns_only_own(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["id"], vps.id)
        self.assertEqual(data["results"][0]["status"], ProvisioningVPS.VPS_STATUS_ACTIVE)
        self.assertEqual(data["results"][0]["restart_modes"], [])
        self.assertFalse(data["can_request_vps"])

    def test_me_vps_post_202_accepts_and_enqueues(self):
        model = self.bc.database.create(
            user=1, academy=1, provisioning_vendor=1, provisioning_academy=1, provisioning_profile=1
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        model.provisioning_profile.academy = model.academy
        model.provisioning_profile.vendor = model.provisioning_vendor
        model.provisioning_profile.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor_settings = {
            "item_ids": ["100"],
            "template_ids": [10],
            "data_center_ids": [5],
        }
        model.provisioning_academy.save()
        with patch("breathecode.provisioning.views.request_vps") as mock_request:
            mock_vps = ProvisioningVPS(
                id=1,
                user=model.user,
                academy=model.academy,
                vendor=model.provisioning_vendor,
                status=ProvisioningVPS.VPS_STATUS_PENDING,
            )
            mock_request.return_value = mock_vps
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps")
            response = self.client.post(
                url,
                {
                    "provisioning_academy": model.provisioning_academy.id,
                    "consumable_id": 99,
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(response.json()["id"], 1)
            self.assertEqual(response.json()["status"], ProvisioningVPS.VPS_STATUS_PENDING)
            mock_request.assert_called_once_with(
                model.user,
                plan_slug=None,
                vendor_selection={"item_id": "100", "template_id": 10, "data_center_id": 5},
                provisioning_academy_id=model.provisioning_academy.id,
                consumable_id=99,
            )

    def test_me_vps_post_digitalocean_vendor_selection(self):
        model = self.bc.database.create(
            user=1, academy=1, provisioning_vendor=1, provisioning_academy=1, provisioning_profile=1
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_profile.academy = model.academy
        model.provisioning_profile.vendor = model.provisioning_vendor
        model.provisioning_profile.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor_settings = {
            "region_slugs": ["nyc1"],
            "size_slugs": ["s-1vcpu-1gb"],
            "image_slugs": ["ubuntu-22-04-x64"],
        }
        model.provisioning_academy.save()
        with patch("breathecode.provisioning.views.request_vps") as mock_request:
            mock_vps = ProvisioningVPS(
                id=2,
                user=model.user,
                academy=model.academy,
                vendor=model.provisioning_vendor,
                status=ProvisioningVPS.VPS_STATUS_PENDING,
            )
            mock_request.return_value = mock_vps
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps")
            response = self.client.post(
                url,
                {
                    "vendor_selection": {
                        "region_slug": "nyc1",
                        "size_slug": "s-1vcpu-1gb",
                        "image_slug": "ubuntu-22-04-x64",
                    },
                    "provisioning_academy": model.provisioning_academy.id,
                    "consumable_id": 88,
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_request.assert_called_once_with(
                model.user,
                plan_slug=None,
                vendor_selection={
                    "region_slug": "nyc1",
                    "size_slug": "s-1vcpu-1gb",
                    "image_slug": "ubuntu-22-04-x64",
                },
                provisioning_academy_id=model.provisioning_academy.id,
                consumable_id=88,
            )

    def test_me_vps_post_accepts_plan_slug_without_consumable_id(self):
        model = self.bc.database.create(
            user=1, academy=1, provisioning_vendor=1, provisioning_academy=1, provisioning_profile=1
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        model.provisioning_profile.academy = model.academy
        model.provisioning_profile.vendor = model.provisioning_vendor
        model.provisioning_profile.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.vendor_settings = {
            "item_ids": ["100"],
            "template_ids": [10],
            "data_center_ids": [5],
        }
        model.provisioning_academy.save()
        with patch("breathecode.provisioning.views.request_vps") as mock_request:
            mock_vps = ProvisioningVPS(
                id=3,
                user=model.user,
                academy=model.academy,
                vendor=model.provisioning_vendor,
                status=ProvisioningVPS.VPS_STATUS_PENDING,
            )
            mock_request.return_value = mock_vps
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps")
            response = self.client.post(
                url,
                {
                    "provisioning_academy": model.provisioning_academy.id,
                    "plan_slug": "full-stack",
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_request.assert_called_once_with(
                model.user,
                plan_slug="full-stack",
                vendor_selection={"item_id": "100", "template_id": 10, "data_center_id": 5},
                provisioning_academy_id=model.provisioning_academy.id,
                consumable_id=None,
            )


class MeVPSByIdViewTestSuite(ProvisioningTestCase):
    def test_me_vps_by_id_404_for_non_owner(self):
        owner_model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        other_model = self.bc.database.create(user=1)
        vps = ProvisioningVPS.objects.create(
            user=owner_model.user,
            academy=owner_model.academy,
            vendor=owner_model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
        )
        other_user = other_model.user
        self.client.force_authenticate(other_user)
        url = reverse_lazy("provisioning:me_vps_id", kwargs={"vps_id": vps.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_me_vps_by_id_200_for_owner(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            hostname="vps.example.com",
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps_id", kwargs={"vps_id": vps.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], vps.id)
        self.assertEqual(response.json()["hostname"], "vps.example.com")


class MeVPSGetListRestartModesTestSuite(ProvisioningTestCase):
    def test_me_vps_get_list_restart_modes_digitalocean_active(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="999",
        )
        self.client.force_authenticate(model.user)
        response = self.client.get(reverse_lazy("provisioning:me_vps"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.json()["results"][0]
        self.assertEqual(row["restart_modes"], sorted(ProvisioningVPS.RestartMode.values))

    def test_me_vps_get_list_restart_modes_empty_without_external_id(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="",
        )
        self.client.force_authenticate(model.user)
        response = self.client.get(reverse_lazy("provisioning:me_vps"))
        self.assertEqual(response.json()["results"][0]["restart_modes"], [])


class MeVPSRestartViewTestSuite(ProvisioningTestCase):
    def test_me_vps_restart_404_non_owner(self):
        owner_model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        other_model = self.bc.database.create(user=1)
        owner_model.provisioning_academy.vendor = owner_model.provisioning_vendor
        owner_model.provisioning_academy.academy = owner_model.academy
        owner_model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=owner_model.user,
            academy=owner_model.academy,
            vendor=owner_model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="99",
        )
        self.client.force_authenticate(other_model.user)
        url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_me_vps_restart_400_not_active(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_PENDING,
            external_id="1",
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_vps_restart_400_no_external_id(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="",
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_vps_restart_400_invalid_mode(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "x"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="123",
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
        response = self.client.post(url, {"mode": "nope"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_vps_restart_400_vendor_without_restart(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "x"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="ext-1",
        )
        self.client.force_authenticate(model.user)
        url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_vps_restart_200_digitalocean(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="12345",
        )
        mock_client = MagicMock()
        mock_client.restart_vps = MagicMock(
            return_value={"action_id": 999, "action_status": "in-progress", "action_type": "power_cycle"}
        )
        with (
            patch(
                "breathecode.provisioning.views.vps_restart_modes_for_list",
                return_value=sorted(ProvisioningVPS.RestartMode.values),
            ),
            patch("breathecode.provisioning.views.get_vps_client", return_value=mock_client),
        ):
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
            response = self.client.post(url, {"mode": "forced"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["action_id"], 999)
        self.assertEqual(data["action_type"], "power_cycle")
        self.assertEqual(data["action_status"], "in-progress")
        mock_client.restart_vps.assert_called_once()
        _args, kwargs = mock_client.restart_vps.call_args
        self.assertEqual(kwargs.get("mode"), "forced")

    def test_me_vps_restart_defaults_to_graceful(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="1",
        )
        mock_client = MagicMock()
        mock_client.restart_vps = MagicMock(
            return_value={"action_id": 1, "action_status": "in-progress", "action_type": "reboot"}
        )
        with (
            patch(
                "breathecode.provisioning.views.vps_restart_modes_for_list",
                return_value=sorted(ProvisioningVPS.RestartMode.values),
            ),
            patch("breathecode.provisioning.views.get_vps_client", return_value=mock_client),
        ):
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
            response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["action_type"], "reboot")
        _args, kwargs = mock_client.restart_vps.call_args
        self.assertEqual(kwargs.get("mode"), "graceful")

    def test_me_vps_restart_502_vendor_error(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="1",
        )
        mock_client = MagicMock()
        mock_client.restart_vps = MagicMock(side_effect=VPSProvisioningError("upstream"))
        with (
            patch(
                "breathecode.provisioning.views.vps_restart_modes_for_list",
                return_value=sorted(ProvisioningVPS.RestartMode.values),
            ),
            patch("breathecode.provisioning.views.get_vps_client", return_value=mock_client),
        ):
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
            response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_me_vps_restart_400_mode_not_allowed_for_vendor_subset(self):
        model = self.bc.database.create(user=1, academy=1, provisioning_vendor=1, provisioning_academy=1)
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.academy = model.academy
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.save()
        vps = ProvisioningVPS.objects.create(
            user=model.user,
            academy=model.academy,
            vendor=model.provisioning_vendor,
            status=ProvisioningVPS.VPS_STATUS_ACTIVE,
            external_id="1",
        )
        mock_client = MagicMock()
        mock_client.restart_vps = MagicMock()
        with (
            patch("breathecode.provisioning.views.vps_restart_modes_for_list", return_value=["graceful"]),
            patch("breathecode.provisioning.views.get_vps_client", return_value=mock_client),
        ):
            self.client.force_authenticate(model.user)
            url = reverse_lazy("provisioning:me_vps_restart", kwargs={"vps_id": vps.id})
            response = self.client.post(url, {"mode": "forced"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_client.restart_vps.assert_not_called()
