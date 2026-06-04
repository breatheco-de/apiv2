"""
Test /v1/provisioning/academy/provisioningprofile
"""

import json
import os
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import ProvisioningTestCase


def get_serializer(provisioning_profile, data={}):
    vendor = provisioning_profile.vendor
    return {
        "id": provisioning_profile.id,
        "vendor": (
            {
                "id": vendor.id,
                "name": vendor.name,
                "workspaces_url": vendor.workspaces_url,
            }
            if vendor
            else None
        ),
        "academy": {
            "id": provisioning_profile.academy.id,
            "name": provisioning_profile.academy.name,
            "slug": provisioning_profile.academy.slug,
        },
        "cohort_ids": list(provisioning_profile.cohorts.values_list("id", flat=True)),
        "member_ids": list(provisioning_profile.members.values_list("id", flat=True)),
        **data,
    }


class ProvisioningTestSuite(ProvisioningTestCase):

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):

        url = reverse_lazy("provisioning:academy_id_provisioning_profile", kwargs={"academy_id": 1})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_profiles(self):

        url = reverse_lazy("provisioning:academy_id_provisioning_profile", kwargs={"academy_id": 1})

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_provisioning_profiles(self):

        url = reverse_lazy("provisioning:academy_id_provisioning_profile", kwargs={"academy_id": 1})

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_profile=1,
            vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.provisioning_profile)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
