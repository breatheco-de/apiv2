"""Tests for GET /provisioning/academy/vendor."""

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.provisioning.models import ProvisioningVendor

from ..mixins import ProvisioningTestCase


class AcademyVendorViewTestSuite(ProvisioningTestCase):
    def test_get_vendor_includes_settings_schema(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_vendor")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertTrue(len(payload) > 0)
        self.assertIn("settings_schema", payload[0])
        self.assertEqual(payload[0]["settings_schema"]["fields"][0]["settings_key"], "item_ids")

    def test_get_vendor_filter_by_vendor_type(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
        )
        v_keep = model.provisioning_vendor
        v_keep.vendor_type = ProvisioningVendor.VendorType.VPS_SERVER
        v_keep.save()
        ProvisioningVendor.objects.create(
            name="OtherVendorTypeFilter",
            vendor_type=ProvisioningVendor.VendorType.LLM,
            workspaces_url="https://llm.example.com",
        )

        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_vendor")

        r_all = self.client.get(url)
        self.assertEqual(r_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_all.json()), 2)

        r_vps = self.client.get(url, {"vendor_type": "VPS_SERVER"})
        self.assertEqual(r_vps.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_vps.json()), 1)
        self.assertEqual(r_vps.json()[0]["id"], v_keep.id)
        self.assertEqual(r_vps.json()[0]["vendor_type"], ProvisioningVendor.VendorType.VPS_SERVER)

    def test_get_vendor_invalid_vendor_type_query(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_vendor")
        response = self.client.get(url, {"vendor_type": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
