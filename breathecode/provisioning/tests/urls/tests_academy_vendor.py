"""Tests for GET /provisioning/academy/vendor."""

from django.urls import reverse_lazy
from rest_framework import status

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
        self.assertEqual(payload[0]["settings_schema"]["fields"][0]["key"], "item_ids")
