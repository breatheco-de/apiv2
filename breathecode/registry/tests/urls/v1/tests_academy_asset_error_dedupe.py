from rest_framework import status

from breathecode.registry.models import AssetErrorLog

from ...mixins import RegistryTestCase


class RegistryTestSuite(RegistryTestCase):
    def test_post_dedupe_noop_when_no_duplicates(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_asset_error",
            asset_category=1,
            asset={"slug": "asset-error-dedupe", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        keeper = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=1,
            status="ERROR",
            status_text="keeper",
        )

        response = self.client.post(
            f"/v1/registry/academy/asset/error/{keeper.id}/dedupe",
            {},
            format="json",
            HTTP_ACADEMY=model.academy.id,
        )
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["deleted_count"], 0)
        self.assertEqual(data["deleted_ids"], [])
        self.assertEqual(data["kept"]["id"], keeper.id)

        self.assertEqual(
            AssetErrorLog.objects.filter(
                slug="invalid-url",
                asset_type=model.asset.asset_type,
                path="README.md",
                asset=model.asset,
            ).count(),
            1,
        )

    def test_post_dedupe_requires_crud_asset_error_capability(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
            asset_category=1,
            asset={"slug": "asset-error-dedupe-perms", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        keeper = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=0,
        )

        response = self.client.post(
            f"/v1/registry/academy/asset/error/{keeper.id}/dedupe",
            {},
            format="json",
            HTTP_ACADEMY=model.academy.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
