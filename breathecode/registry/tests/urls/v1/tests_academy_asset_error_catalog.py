from unittest.mock import patch

from rest_framework import status

from breathecode.authenticate.models import ProfileAcademy
from breathecode.registry.utils import (
    ASSET_ERROR_LOG_CATALOG_METADATA,
    AssetErrorLogType,
    get_asset_error_log_catalog,
)

from ...mixins import RegistryTestCase


class RegistryTestSuite(RegistryTestCase):
    def test_get_catalog_requires_read_asset_error_capability(self):
        model = self.generate_models(authenticate=True, profile_academy=1)
        self.client.force_authenticate(user=model.user)

        response = self.client.get("/v1/registry/academy/asset/error/catalog", HTTP_ACADEMY=model.academy.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_catalog_returns_full_metadata(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
        )
        self.client.force_authenticate(user=model.user)

        response = self.client.get("/v1/registry/academy/asset/error/catalog", HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), len(get_asset_error_log_catalog()))
        self.assertIn("slug", data[0])
        self.assertIn("label", data[0])
        self.assertIn("description", data[0])
        self.assertIn("common_trigger_situations", data[0])
        self.assertIn("severity_hint", data[0])
        self.assertIn("status_notes", data[0])

    def test_get_catalog_read_aggregate_partial_scope_returns_meta(self):
        model = self.generate_models(
            authenticate=True,
            academy=2,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
        )
        self.client.force_authenticate(user=model.user)

        response = self.client.get("/v1/registry/academy/asset/error/catalog", HTTP_ACADEMY="1,2")
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["academy_scope"]["requested_academy_ids"], [1, 2])
        self.assertEqual(data["academy_scope"]["applied_academy_ids"], [1])
        self.assertEqual(data["academy_scope"]["resolution"], "partial")
        self.assertGreater(len(data["results"]), 0)

    def test_get_catalog_read_aggregate_full_scope_returns_list(self):
        model = self.generate_models(
            authenticate=True,
            academy=2,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
        )
        self.client.force_authenticate(user=model.user)

        pa = model.profile_academy
        ProfileAcademy.objects.create(
            user=pa.user,
            academy_id=2,
            role=pa.role,
            email=pa.email,
            first_name=pa.first_name,
            last_name=pa.last_name,
            status="ACTIVE",
        )

        response = self.client.get("/v1/registry/academy/asset/error/catalog", HTTP_ACADEMY="1,2")
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(data, list)
        self.assertEqual({item["slug"] for item in data}, {item["slug"] for item in get_asset_error_log_catalog()})

    def test_get_catalog_returns_fallback_when_metadata_missing(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
        )
        self.client.force_authenticate(user=model.user)

        with patch.dict(ASSET_ERROR_LOG_CATALOG_METADATA, {AssetErrorLogType.INVALID_URL: {}}, clear=False):
            response = self.client.get("/v1/registry/academy/asset/error/catalog", HTTP_ACADEMY=model.academy.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(x for x in response.json() if x["slug"] == AssetErrorLogType.INVALID_URL)
        self.assertEqual(item["label"], "Unknown error")
        self.assertEqual(item["severity_hint"], "unknown")
