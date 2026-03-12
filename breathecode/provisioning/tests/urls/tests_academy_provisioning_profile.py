"""
Tests for GET/POST /v1/provisioning/academy/provisioningprofile and
GET/PUT/DELETE /v1/provisioning/academy/provisioningprofile/<profile_id> (academy from header).
"""

from django.urls import reverse_lazy
from rest_framework import status

from ..mixins import ProvisioningTestCase


def profile_serializer(profile):
    vendor = profile.vendor
    return {
        "id": profile.id,
        "vendor": (
            {"id": vendor.id, "name": vendor.name, "workspaces_url": vendor.workspaces_url}
            if vendor
            else None
        ),
        "academy": {
            "id": profile.academy.id,
            "name": profile.academy.name,
            "slug": profile.academy.slug,
        },
        "cohort_ids": list(profile.cohorts.values_list("id", flat=True)),
        "member_ids": list(profile.members.values_list("id", flat=True)),
    }


class AcademyProvisioningProfileTestSuite(ProvisioningTestCase):
    def test_get_list_without_auth(self):
        url = reverse_lazy("provisioning:academy_provisioning_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_list_without_capability(self):
        model = self.bc.database.create(user=1, profile_academy=1)
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_list_empty(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_post_create_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_profile")
        response = self.client.post(url, data={"vendor_id": model.provisioning_vendor.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["vendor"]["id"], model.provisioning_vendor.id)
        self.assertEqual(data["academy"]["id"], 1)
        self.assertEqual(data["cohort_ids"], [])
        self.assertEqual(data["member_ids"], [])

    def test_post_create_vendor_not_found(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_profile")
        response = self.client.post(url, data={"vendor_id": 999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json().get("slug"), "vendor-not-found")

    def test_get_by_id_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_profile=1,
            provisioning_vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_profile_id",
            kwargs={"profile_id": model.provisioning_profile.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), profile_serializer(model.provisioning_profile))

    def test_get_by_id_not_found(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_profile_id",
            kwargs={"profile_id": 999},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_update_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_profile=1,
            provisioning_vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_profile_id",
            kwargs={"profile_id": model.provisioning_profile.id},
        )
        response = self.client.put(
            url, data={"vendor_id": model.provisioning_vendor.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_profile=1,
            provisioning_vendor=1,
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_profile_id",
            kwargs={"profile_id": model.provisioning_profile.id},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
