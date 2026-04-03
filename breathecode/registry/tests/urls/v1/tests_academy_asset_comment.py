from rest_framework import status

from breathecode.authenticate.models import ProfileAcademy
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

    def test_get_comments_academies_query_param_scopes_to_allowed_ids(self):
        model = self.generate_models(
            authenticate=True,
            academy=2,
            profile_academy=1,
            role=1,
            capability="read_asset",
            asset_category=2,
            asset=[
                {"slug": "asset-ac1", "academy_id": 1, "category_id": 1},
                {"slug": "asset-ac2", "academy_id": 2, "category_id": 2},
            ],
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

        comment_one = AssetComment.objects.create(asset=model.asset[0], text="on-academy-one")
        comment_two = AssetComment.objects.create(asset=model.asset[1], text="on-academy-two")

        url = "/v1/registry/academy/asset/comment?academies=1,2"
        response = self.client.get(url, HTTP_ACADEMY=model.academy[0].id)
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({x["id"] for x in data}, {comment_one.id, comment_two.id})

        url_only_two = "/v1/registry/academy/asset/comment?academies=2"
        response_two = self.client.get(url_only_two, HTTP_ACADEMY=model.academy[0].id)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)
        self.assertEqual({x["id"] for x in response_two.json()}, {comment_two.id})

    def test_get_comments_academies_without_capability_returns_empty(self):
        model = self.generate_models(
            authenticate=True,
            academy=2,
            profile_academy=1,
            role=1,
            capability="read_asset",
            asset_category=2,
            asset=[
                {"slug": "x1", "academy_id": 1, "category_id": 1},
                {"slug": "x2", "academy_id": 2, "category_id": 2},
            ],
        )
        self.client.force_authenticate(user=model.user)

        AssetComment.objects.create(asset=model.asset[1], text="other-academy")

        url = "/v1/registry/academy/asset/comment?academies=2"
        response = self.client.get(url, HTTP_ACADEMY=model.academy[0].id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_get_comments_academies_non_integer_returns_400(self):
        model = self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
            capability="read_asset",
            asset_category=1,
            asset={"slug": "only-one", "academy_id": 1, "category_id": 1},
        )
        self.client.force_authenticate(user=model.user)

        response = self.client.get(
            "/v1/registry/academy/asset/comment?academies=1,not-a-number",
            HTTP_ACADEMY=model.academy.id,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
