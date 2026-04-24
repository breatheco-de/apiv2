from rest_framework import status

from breathecode.registry.models import AssetErrorLog

from ...mixins import RegistryTestCase


class RegistryTestSuite(RegistryTestCase):
    def test_get_errors_includes_priority(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
            asset_category=1,
            asset={"slug": "asset-errors-priority", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        error = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=9,
        )

        response = self.client.get("/v1/registry/academy/asset/error", HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(x for x in data if x["id"] == error.id)
        self.assertEqual(row["priority"], 9)

    def test_get_errors_sort_by_priority(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset_error",
            asset_category=1,
            asset={"slug": "asset-errors-sort", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        low = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=1,
        )
        high = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="empty-readme",
            path="README.md",
            priority=5,
        )

        response = self.client.get("/v1/registry/academy/asset/error?sort=-priority", HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [x["id"] for x in data if x["id"] in [low.id, high.id]]
        self.assertEqual(ids[:2], [high.id, low.id])

    def test_put_error_updates_priority(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_asset_error",
            asset_category=1,
            asset={"slug": "asset-error-update-priority", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        error = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=0,
        )

        response = self.client.put(
            "/v1/registry/academy/asset/error",
            {"id": error.id, "priority": 3},
            format="json",
            HTTP_ACADEMY=model.academy.id,
        )
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data[0]["priority"], 3)
        error.refresh_from_db()
        self.assertEqual(error.priority, 3)

    def test_put_errors_updates_priority_in_bulk(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="crud_asset_error",
            asset_category=1,
            asset={"slug": "asset-error-update-priority-bulk", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        first = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="invalid-url",
            path="README.md",
            priority=0,
        )
        second = AssetErrorLog.objects.create(
            asset=model.asset,
            asset_type=model.asset.asset_type,
            slug="empty-readme",
            path="README.md",
            priority=0,
        )

        payload = [{"id": first.id, "priority": 2}, {"id": second.id, "priority": 4}]
        response = self.client.put("/v1/registry/academy/asset/error", payload, format="json", HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({x["id"] for x in data}, {first.id, second.id})
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.priority, 2)
        self.assertEqual(second.priority, 4)
