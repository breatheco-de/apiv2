from rest_framework import status

from breathecode.registry.models import AssetComment

from ...mixins import RegistryTestCase


class RegistryTestSuite(RegistryTestCase):
    def test_get_comments_filter_by_asset_ids(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset",
            asset_category=1,
            asset=[
                {"slug": "asset-one", "academy_id": 1, "category_id": 1},
                {"slug": "asset-two", "academy_id": 1, "category_id": 1},
                {"slug": "asset-three", "academy_id": 1, "category_id": 1},
            ],
        )
        self.client.force_authenticate(user=model.user)

        comment_one = AssetComment.objects.create(asset=model.asset[0], text="comment-one")
        comment_two = AssetComment.objects.create(asset=model.asset[1], text="comment-two")
        AssetComment.objects.create(asset=model.asset[2], text="comment-three")

        url = f"/v1/registry/academy/asset/comment?asset={model.asset[0].id},{model.asset[1].id}"
        response = self.client.get(url, HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({x["id"] for x in data}, {comment_one.id, comment_two.id})

    def test_get_comments_filter_by_mixed_asset_id_and_slug(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset",
            asset_category=1,
            asset=[
                {"slug": "asset-alpha", "academy_id": 1, "category_id": 1},
                {"slug": "asset-beta", "academy_id": 1, "category_id": 1},
                {"slug": "asset-gamma", "academy_id": 1, "category_id": 1},
            ],
        )
        self.client.force_authenticate(user=model.user)

        comment_alpha = AssetComment.objects.create(asset=model.asset[0], text="comment-alpha")
        comment_beta = AssetComment.objects.create(asset=model.asset[1], text="comment-beta")
        AssetComment.objects.create(asset=model.asset[2], text="comment-gamma")

        url = f"/v1/registry/academy/asset/comment?asset={model.asset[0].id},{model.asset[1].slug}"
        response = self.client.get(url, HTTP_ACADEMY=model.academy.id)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({x["id"] for x in data}, {comment_alpha.id, comment_beta.id})
