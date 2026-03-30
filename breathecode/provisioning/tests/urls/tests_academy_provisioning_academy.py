"""
Tests for GET/POST /v1/provisioning/academy/provisioningacademy and
GET/PUT /v1/provisioning/academy/provisioningacademy/<id> (academy from header; credentials masked).
"""

from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningVendor

from ..mixins import ProvisioningTestCase


def pa_serializer(pa):
    return {
        "id": pa.id,
        "vendor": (
            {"id": pa.vendor.id, "name": pa.vendor.name, "workspaces_url": pa.vendor.workspaces_url}
            if pa.vendor
            else None
        ),
        "academy_id": pa.academy_id,
        "credentials_set": bool(pa.credentials_token or pa.credentials_key),
        "vendor_settings": pa.vendor_settings or {},
        "connection_status": pa.connection_status,
        "connection_status_text": pa.connection_status_text,
        "connection_test_at": pa.connection_test_at.isoformat().replace("+00:00", "Z")
        if pa.connection_test_at
        else None,
        "container_idle_timeout": pa.container_idle_timeout,
        "max_active_containers": pa.max_active_containers,
        "created_at": pa.created_at.isoformat() if pa.created_at else None,
        "updated_at": pa.updated_at.isoformat() if pa.updated_at else None,
    }


class AcademyProvisioningAcademyTestSuite(ProvisioningTestCase):
    def test_get_list_without_auth(self):
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_list_empty(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_get_list_filter_by_vendor_type(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        academy_id = model.profile_academy.academy_id
        v_vps = model.provisioning_vendor
        v_vps.vendor_type = ProvisioningVendor.VendorType.VPS_SERVER
        v_vps.save()
        pa_vps = model.provisioning_academy
        pa_vps.academy_id = academy_id
        pa_vps.vendor = v_vps
        pa_vps.save()

        v_editor = ProvisioningVendor.objects.create(
            name="GitpodFilterTest",
            vendor_type=ProvisioningVendor.VendorType.CODING_EDITOR,
            workspaces_url="https://gitpod.example.com",
        )
        pa_editor = ProvisioningAcademy.objects.create(
            academy_id=academy_id,
            vendor=v_editor,
            credentials_token="t",
            credentials_key="",
        )

        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")

        r_all = self.client.get(url)
        self.assertEqual(r_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_all.json()), 2)

        r_vps = self.client.get(url, {"vendor_type": "vps_server"})
        self.assertEqual(r_vps.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_vps.json()), 1)
        self.assertEqual(r_vps.json()[0]["id"], pa_vps.id)
        self.assertEqual(r_vps.json()[0]["vendor"]["vendor_type"], ProvisioningVendor.VendorType.VPS_SERVER)

        r_editor = self.client.get(url, {"vendor_type": "CODING_EDITOR"})
        self.assertEqual(r_editor.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r_editor.json()), 1)
        self.assertEqual(r_editor.json()[0]["id"], pa_editor.id)

    def test_get_list_invalid_vendor_type_query(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
        )
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.get(url, {"vendor_type": "not-a-real-type"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.post(
            url,
            data={
                "vendor_id": model.provisioning_vendor.id,
                "credentials_token": "token123",
                "container_idle_timeout": 20,
                "max_active_containers": 3,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("credentials_set", data)
        self.assertTrue(data["credentials_set"])
        self.assertNotIn("credentials_token", data)
        self.assertEqual(data["vendor"]["id"], model.provisioning_vendor.id)
        self.assertEqual(int(data["academy_id"]), model.profile_academy.academy_id)
        self.assertEqual(data["container_idle_timeout"], 20)
        self.assertEqual(data["max_active_containers"], 3)
        self.assertEqual(data["vendor_settings"], {})
        self.assertEqual(data["connection_status"], ProvisioningAcademy.ConnectionStatus.UNTESTED)
        self.assertEqual(data["connection_status_text"], "")
        self.assertIsNone(data["connection_test_at"])

    def test_post_create_duplicate_academy_vendor(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor_id = model.provisioning_vendor.id
        model.provisioning_academy.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        response = self.client.post(
            url,
            data={
                "vendor_id": model.provisioning_vendor.id,
                "credentials_token": "token",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_by_id_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor_id = model.provisioning_vendor.id
        model.provisioning_academy.credentials_token = "secret"
        model.provisioning_academy.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_id",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["credentials_set"])
        self.assertNotIn("credentials_token", data)

    def test_get_list_and_detail_include_connection_health(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        pa = model.provisioning_academy
        pa.academy_id = model.profile_academy.academy_id
        pa.vendor_id = model.provisioning_vendor.id
        tested_at = timezone.now()
        pa.connection_status = ProvisioningAcademy.ConnectionStatus.OK
        pa.connection_status_text = "API reachable"
        pa.connection_test_at = tested_at
        pa.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        list_url = reverse_lazy("provisioning:academy_provisioning_academy")
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        row = list_response.json()[0]
        self.assertEqual(row["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)
        self.assertEqual(row["connection_status_text"], "API reachable")
        self.assertIsNotNone(row["connection_test_at"])

        detail_url = reverse_lazy(
            "provisioning:academy_provisioning_academy_id",
            kwargs={"provisioning_academy_id": pa.id},
        )
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        body = detail_response.json()
        self.assertEqual(body["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)
        self.assertEqual(body["connection_status_text"], "API reachable")
        self.assertEqual(body["connection_test_at"], row["connection_test_at"])

    def test_put_update_success(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor_id = model.provisioning_vendor.id
        model.provisioning_academy.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_id",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.put(
            url,
            data={"container_idle_timeout": 30, "max_active_containers": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["container_idle_timeout"], 30)
        self.assertEqual(response.json()["max_active_containers"], 5)

    def test_post_create_hostinger_vendor_settings(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        payload = {
            "vendor_id": model.provisioning_vendor.id,
            "credentials_token": "token123",
            "vendor_settings": {
                "item_ids": ["100", "101"],
                "template_ids": [11, 12],
                "data_center_ids": [1, 2],
            },
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["vendor_settings"]["item_ids"], ["100", "101"])

    def test_post_create_hostinger_vendor_settings_optional_empty(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        payload = {
            "vendor_id": model.provisioning_vendor.id,
            "credentials_token": "token123",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["vendor_settings"], {})

    def test_post_create_invalid_vendor_settings_key(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        payload = {
            "vendor_id": model.provisioning_vendor.id,
            "credentials_token": "token123",
            "vendor_settings": {
                "unknown": ["x"],
                "item_ids": ["100"],
                "template_ids": [11],
                "data_center_ids": [1],
            },
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_create_digitalocean_vendor_settings(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        payload = {
            "vendor_id": model.provisioning_vendor.id,
            "credentials_token": "token123",
            "vendor_settings": {
                "region_slugs": ["nyc1", "sfo3"],
                "size_slugs": ["s-1vcpu-1gb"],
                "image_slugs": ["ubuntu-22-04-x64"],
            },
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["vendor_settings"]["region_slugs"], ["nyc1", "sfo3"])

    def test_post_create_invalid_digitalocean_vendor_settings_key(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        self.client.force_authenticate(model.user)
        self.headers(academy=1)
        url = reverse_lazy("provisioning:academy_provisioning_academy")
        payload = {
            "vendor_id": model.provisioning_vendor.id,
            "credentials_token": "token123",
            "vendor_settings": {
                "unknown": ["x"],
                "region_slugs": ["nyc1"],
                "size_slugs": ["s-1vcpu-1gb"],
                "image_slugs": ["ubuntu-22-04-x64"],
            },
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.provisioning.views._get_hostinger_vendor_options")
    def test_get_vendor_options_returns_all_hostinger_options(self, options_mock):
        options_mock.return_value = {
            "catalog_items": [{"id": "100", "name": "A"}, {"id": "200", "name": "B"}],
            "templates": [{"id": 11, "name": "Ubuntu"}, {"id": 12, "name": "Debian"}],
            "data_centers": [{"id": 1, "name": "US"}, {"id": 2, "name": "EU"}],
        }
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.vendor_settings = {
            "item_ids": ["100"],
            "template_ids": [11],
            "data_center_ids": [2],
        }
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_vendor_options",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["catalog_items"], [{"id": "100", "name": "A"}, {"id": "200", "name": "B"}])
        self.assertEqual(response.json()["templates"], [{"id": 11, "name": "Ubuntu"}, {"id": 12, "name": "Debian"}])
        self.assertEqual(response.json()["data_centers"], [{"id": 1, "name": "US"}, {"id": 2, "name": "EU"}])

    @patch("breathecode.provisioning.views._get_digitalocean_vendor_options")
    def test_get_vendor_options_returns_all_digitalocean_options(self, options_mock):
        options_mock.return_value = {
            "regions": [{"slug": "nyc1", "name": "NYC 1"}],
            "sizes": [{"slug": "s-1vcpu-1gb"}],
            "images": [{"slug": "ubuntu-22-04-x64", "distribution": "Ubuntu"}],
        }
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "tok"
        model.provisioning_academy.vendor_settings = {
            "region_slugs": ["nyc1"],
            "size_slugs": ["s-1vcpu-1gb"],
            "image_slugs": ["ubuntu-22-04-x64"],
        }
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_vendor_options",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["regions"], [{"slug": "nyc1", "name": "NYC 1"}])
        self.assertEqual(response.json()["sizes"], [{"slug": "s-1vcpu-1gb"}])
        self.assertEqual(response.json()["images"], [{"slug": "ubuntu-22-04-x64", "distribution": "Ubuntu"}])

    @patch("breathecode.provisioning.views.get_coding_editor_client")
    def test_post_test_connection_codespaces_success(self, get_coding_editor_client_mock):
        editor_client = type("EditorClientMock", (), {"test_connection": lambda *args, **kwargs: None})()
        get_coding_editor_client_mock.return_value = editor_client
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "codespaces"
        model.provisioning_vendor.vendor_type = "CODING_EDITOR"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "gh-token"
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)
        self.assertEqual(response.json()["connection_status_text"], "vendor-connection-check-succeeded")
        self.assertIsNotNone(response.json()["connection_test_at"])

    @patch("breathecode.provisioning.views.get_coding_editor_client")
    def test_post_test_connection_codespaces_error(self, get_coding_editor_client_mock):
        class EditorClientMock:
            def test_connection(self, *args, **kwargs):
                raise Exception("invalid token")

        get_coding_editor_client_mock.return_value = EditorClientMock()
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "codespaces"
        model.provisioning_vendor.vendor_type = "CODING_EDITOR"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "gh-token"
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.ERROR)
        self.assertIn("invalid token", response.json()["connection_status_text"])
        self.assertIsNotNone(response.json()["connection_test_at"])

    @patch("breathecode.provisioning.views.get_vps_client")
    def test_post_test_connection_hostinger_success(self, get_vps_client_mock):
        vps_client = type("VPSClientMock", (), {"test_connection": lambda *args, **kwargs: None})()
        get_vps_client_mock.return_value = vps_client
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.vendor_type = "VPS_SERVER"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "h-token"
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)
        self.assertEqual(response.json()["connection_status_text"], "vendor-connection-check-succeeded")
        self.assertIsNotNone(response.json()["connection_test_at"])

    def test_post_test_connection_hostinger_error_when_missing_token(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "hostinger"
        model.provisioning_vendor.vendor_type = "VPS_SERVER"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = ""
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.ERROR)
        self.assertIn("Hostinger credentials missing token", response.json()["connection_status_text"])
        self.assertIsNotNone(response.json()["connection_test_at"])

    @patch("breathecode.provisioning.views.get_vps_client")
    def test_post_test_connection_digitalocean_success(self, get_vps_client_mock):
        vps_client = type("VPSClientMock", (), {"test_connection": lambda *args, **kwargs: None})()
        get_vps_client_mock.return_value = vps_client
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.vendor_type = "VPS_SERVER"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = "do-token"
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.OK)

    def test_post_test_connection_digitalocean_error_when_missing_token(self):
        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="crud_provisioning_activity",
            provisioning_vendor=1,
            provisioning_academy=1,
        )
        model.provisioning_vendor.name = "digitalocean"
        model.provisioning_vendor.vendor_type = "VPS_SERVER"
        model.provisioning_vendor.save()
        model.provisioning_academy.academy_id = model.profile_academy.academy_id
        model.provisioning_academy.vendor = model.provisioning_vendor
        model.provisioning_academy.credentials_token = ""
        model.provisioning_academy.save()

        self.client.force_authenticate(model.user)
        self.headers(academy=model.profile_academy.academy_id)
        url = reverse_lazy(
            "provisioning:academy_provisioning_academy_test_connection",
            kwargs={"provisioning_academy_id": model.provisioning_academy.id},
        )
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["connection_status"], ProvisioningAcademy.ConnectionStatus.ERROR)
        self.assertIn("DigitalOcean credentials missing token", response.json()["connection_status_text"])
