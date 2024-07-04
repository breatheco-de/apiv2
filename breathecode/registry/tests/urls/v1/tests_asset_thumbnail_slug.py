"""
Test /answer
"""

from random import randint
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.registry.actions import AssetThumbnailGenerator

from ...mixins import RegistryTestCase


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET without Asset
    """

    @patch("breathecode.registry.actions.AssetThumbnailGenerator.__init__", MagicMock(return_value=None))
    def test__get__without_asset(self):
        cases = [(True, status.HTTP_301_MOVED_PERMANENTLY), (False, status.HTTP_302_FOUND)]
        url = reverse_lazy("registry:asset_thumbnail_slug", kwargs={"asset_slug": "slug"})

        for redirect_permanently, current_status in cases:
            redirect_url = self.bc.fake.url()
            with patch(
                "breathecode.registry.actions.AssetThumbnailGenerator.get_thumbnail_url",
                MagicMock(return_value=(redirect_url, redirect_permanently)),
            ):
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                expected = ""

                self.assertEqual(content, expected)
                self.assertEqual(response.url, redirect_url)
                self.assertEqual(response.status_code, current_status)
                self.assertEqual(self.bc.database.list_of("registry.Asset"), [])
                self.assertEqual(AssetThumbnailGenerator.__init__.call_args_list, [call(None, 0, 0)])
                self.assertEqual(AssetThumbnailGenerator.get_thumbnail_url.call_args_list, [call()])

                # teardown
                AssetThumbnailGenerator.__init__.call_args_list = []
                AssetThumbnailGenerator.get_thumbnail_url.call_args_list = []

    """
    🔽🔽🔽 GET without Asset, passing width and height
    """

    @patch("breathecode.registry.actions.AssetThumbnailGenerator.__init__", MagicMock(return_value=None))
    def test__get__without_asset__passing_width__passing_height(self):
        cases = [(True, status.HTTP_301_MOVED_PERMANENTLY), (False, status.HTTP_302_FOUND)]

        width = randint(1, 2000)
        height = randint(1, 2000)
        url = (
            reverse_lazy("registry:asset_thumbnail_slug", kwargs={"asset_slug": "slug"})
            + f"?width={width}&height={height}"
        )

        for redirect_permanently, current_status in cases:
            redirect_url = self.bc.fake.url()
            with patch(
                "breathecode.registry.actions.AssetThumbnailGenerator.get_thumbnail_url",
                MagicMock(return_value=(redirect_url, redirect_permanently)),
            ):
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                expected = ""

                self.assertEqual(content, expected)
                self.assertEqual(response.url, redirect_url)
                self.assertEqual(response.status_code, current_status)
                self.assertEqual(self.bc.database.list_of("registry.Asset"), [])

                self.assertEqual(
                    str(AssetThumbnailGenerator.__init__.call_args_list),
                    str(
                        [
                            call(None, width, height),
                        ]
                    ),
                )
                self.assertEqual(AssetThumbnailGenerator.get_thumbnail_url.call_args_list, [call()])

                # teardown
                AssetThumbnailGenerator.__init__.call_args_list = []
                AssetThumbnailGenerator.get_thumbnail_url.call_args_list = []

    """
    🔽🔽🔽 GET with Asset
    """

    @patch("breathecode.registry.actions.AssetThumbnailGenerator.__init__", MagicMock(return_value=None))
    def test__get__with_asset(self):
        cases = [(True, status.HTTP_301_MOVED_PERMANENTLY), (False, status.HTTP_302_FOUND)]
        model = self.bc.database.create(asset=1)

        url = reverse_lazy("registry:asset_thumbnail_slug", kwargs={"asset_slug": model.asset.slug})

        for redirect_permanently, current_status in cases:
            redirect_url = self.bc.fake.url()
            with patch(
                "breathecode.registry.actions.AssetThumbnailGenerator.get_thumbnail_url",
                MagicMock(return_value=(redirect_url, redirect_permanently)),
            ):
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                expected = ""

                self.assertEqual(content, expected)
                self.assertEqual(response.url, redirect_url)
                self.assertEqual(response.status_code, current_status)
                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

                self.assertEqual(AssetThumbnailGenerator.__init__.call_args_list, [call(model.asset, 0, 0)])
                self.assertEqual(AssetThumbnailGenerator.get_thumbnail_url.call_args_list, [call()])

                # teardown
                AssetThumbnailGenerator.__init__.call_args_list = []
                AssetThumbnailGenerator.get_thumbnail_url.call_args_list = []

    """
    🔽🔽🔽 GET with Asset, passing width and height
    """

    @patch("breathecode.registry.actions.AssetThumbnailGenerator.__init__", MagicMock(return_value=None))
    def test__get__with_asset__passing_width__passing_height(self):
        cases = [(True, status.HTTP_301_MOVED_PERMANENTLY), (False, status.HTTP_302_FOUND)]
        model = self.bc.database.create(asset=1)

        width = randint(1, 2000)
        height = randint(1, 2000)
        url = (
            reverse_lazy("registry:asset_thumbnail_slug", kwargs={"asset_slug": model.asset.slug})
            + f"?width={width}&height={height}"
        )

        for redirect_permanently, current_status in cases:
            redirect_url = self.bc.fake.url()
            with patch(
                "breathecode.registry.actions.AssetThumbnailGenerator.get_thumbnail_url",
                MagicMock(return_value=(redirect_url, redirect_permanently)),
            ):
                response = self.client.get(url)

                content = self.bc.format.from_bytes(response.content)
                expected = ""

                self.assertEqual(content, expected)
                self.assertEqual(response.url, redirect_url)
                self.assertEqual(response.status_code, current_status)
                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

                self.assertEqual(
                    str(AssetThumbnailGenerator.__init__.call_args_list),
                    str(
                        [
                            call(model.asset, width, height),
                        ]
                    ),
                )
                self.assertEqual(AssetThumbnailGenerator.get_thumbnail_url.call_args_list, [call()])

                # teardown
                AssetThumbnailGenerator.__init__.call_args_list = []
                AssetThumbnailGenerator.get_thumbnail_url.call_args_list = []
