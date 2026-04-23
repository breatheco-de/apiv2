"""Tests for GET/POST /provisioning/academy/vps and DELETE /provisioning/academy/vps/<id>."""

from unittest.mock import patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningVPS

from ..mixins import ProvisioningTestCase


class AcademyVPSViewTestSuite(ProvisioningTestCase):
    def test_academy_vps_post_without_auth(self):
        url = reverse_lazy("provisioning:academy_vps")
        response = self.client.post(url, {"user_id": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_vps_post_without_capability(self):
        model = self.bc.database.create(user=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_vps")
        response = self.client.post(url, {"user_id": model.user.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("breathecode.provisioning.views.get_vps_provisioning_academy_for_academy")
    def test_academy_vps_post_202_accepts_and_enqueues(self, provisioning_academy_mock):
        staff_model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            academy=1,
            provisioning_vendor=1,
        )
        provisioning_academy = self.bc.database.create(provisioning_academy=1).provisioning_academy
        provisioning_academy.vendor = staff_model.provisioning_vendor
        provisioning_academy.vendor.name = "hostinger"
        provisioning_academy.vendor.save()
        provisioning_academy.vendor_settings = {
            "item_ids": ["100"],
            "template_ids": [10],
            "data_center_ids": [5],
        }
        provisioning_academy.save()
        provisioning_academy_mock.return_value = (staff_model.academy, provisioning_academy)
        student_model = self.bc.database.create(user=1)
        student = student_model.user
        with patch("breathecode.provisioning.views.request_vps_for_student") as mock_request:
            mock_vps = ProvisioningVPS(
                id=1,
                user=student,
                academy=staff_model.academy,
                vendor=staff_model.provisioning_vendor,
                status=ProvisioningVPS.VPS_STATUS_PENDING,
            )
            mock_request.return_value = mock_vps
            self.client.force_authenticate(staff_model.user)
            self.headers(academy=staff_model.academy.id)
            url = reverse_lazy("provisioning:academy_vps")
            response = self.client.post(url, {"user_id": student.id, "plan_slug": "full-stack"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(response.json()["id"], 1)
            self.assertEqual(response.json()["status"], ProvisioningVPS.VPS_STATUS_PENDING)
            mock_request.assert_called_once_with(
                student,
                staff_model.academy,
                plan_slug="full-stack",
                vendor_selection={"item_id": "100", "template_id": 10, "data_center_id": 5},
                lang="en",
            )

    @patch("breathecode.provisioning.views.get_vps_provisioning_academy_for_academy")
    def test_academy_vps_post_digitalocean_vendor_selection(self, provisioning_academy_mock):
        staff_model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            academy=1,
            provisioning_vendor=1,
        )
        provisioning_academy = self.bc.database.create(provisioning_academy=1).provisioning_academy
        provisioning_academy.vendor = staff_model.provisioning_vendor
        provisioning_academy.vendor.name = "digitalocean"
        provisioning_academy.vendor.save()
        provisioning_academy.vendor_settings = {
            "region_slugs": ["nyc1"],
            "size_slugs": ["s-1vcpu-1gb"],
            "image_slugs": ["ubuntu-22-04-x64"],
        }
        provisioning_academy.save()
        provisioning_academy_mock.return_value = (staff_model.academy, provisioning_academy)
        student_model = self.bc.database.create(user=1)
        student = student_model.user
        with patch("breathecode.provisioning.views.request_vps_for_student") as mock_request:
            mock_vps = ProvisioningVPS(
                id=2,
                user=student,
                academy=staff_model.academy,
                vendor=staff_model.provisioning_vendor,
                status=ProvisioningVPS.VPS_STATUS_PENDING,
            )
            mock_request.return_value = mock_vps
            self.client.force_authenticate(staff_model.user)
            self.headers(academy=staff_model.academy.id)
            url = reverse_lazy("provisioning:academy_vps")
            response = self.client.post(
                url,
                {
                    "user_id": student.id,
                    "plan_slug": "backend",
                    "vendor_selection": {
                        "region_slug": "nyc1",
                        "size_slug": "s-1vcpu-1gb",
                        "image_slug": "ubuntu-22-04-x64",
                    },
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_request.assert_called_once_with(
                student,
                staff_model.academy,
                plan_slug="backend",
                vendor_selection={
                    "region_slug": "nyc1",
                    "size_slug": "s-1vcpu-1gb",
                    "image_slug": "ubuntu-22-04-x64",
                },
                lang="en",
            )

    def test_academy_vps_post_user_not_found(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            academy=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=model.academy.id)
        url = reverse_lazy("provisioning:academy_vps")
        response = self.client.post(url, {"user_id": 99999, "plan_slug": "full-stack"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("user-not-found", response.content.decode())
