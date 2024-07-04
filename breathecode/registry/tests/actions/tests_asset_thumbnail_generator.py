"""
Test /answer
"""

from random import randint
from unittest.mock import MagicMock, call, patch
from breathecode.registry import tasks

from breathecode.registry.actions import AssetThumbnailGenerator
from ..mixins import RegistryTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET without and with Asset
    """

    def test__constructor(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1)
        cases = [
            ((None,), (None, 0, 0)),
            ((None, 0, 0), (None, 0, 0)),
            ((None, width, height), (None, width, height)),
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in cases:
            generator = AssetThumbnailGenerator(*args)

            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_default_url without preview
    """

    def test__get_default_url__without_preview(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1)
        constructor_cases = [
            ((None,), (None, 0, 0)),
            ((None, 0, 0), (None, 0, 0)),
            ((None, width, 0), (None, width, 0)),
            ((None, 0, height), (None, 0, height)),
            ((None, width, height), (None, width, height)),
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        urls = ["", self.bc.fake.url()]

        for url in urls:
            for args, result in constructor_cases:
                generator = AssetThumbnailGenerator(*args)
                with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": url}))):
                    default_url = generator._get_default_url()

                self.assertEqual(default_url, url)
                self.assertEqual(generator.asset, result[0])
                self.assertEqual(generator.width, result[1])
                self.assertEqual(generator.height, result[2])

                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

    """
    🔽🔽🔽 _get_default_url with preview
    """

    def test__get_default_url__with_preview(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        asset = {"preview": self.bc.fake.url()}
        model = self.bc.database.create(asset=asset)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        urls = ["", self.bc.fake.url()]

        for url in urls:
            for args, result in constructor_cases:
                generator = AssetThumbnailGenerator(*args)
                with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": url}))):
                    default_url = generator._get_default_url()

                self.assertEqual(default_url, url)
                self.assertEqual(generator.asset, result[0])
                self.assertEqual(generator.width, result[1])
                self.assertEqual(generator.height, result[2])

                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

    """
    🔽🔽🔽 _get_asset_url without preview
    """

    def test__get_asset_url__without_preview(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1)
        constructor_cases = [
            ((None,), (None, 0, 0)),
            ((None, 0, 0), (None, 0, 0)),
            ((None, width, 0), (None, width, 0)),
            ((None, 0, height), (None, 0, height)),
            ((None, width, height), (None, width, height)),
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        urls = ["", self.bc.fake.url()]

        for url in urls:
            for args, result in constructor_cases:
                generator = AssetThumbnailGenerator(*args)
                with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": url}))):
                    default_url = generator._get_asset_url()

                self.assertEqual(default_url, url)
                self.assertEqual(generator.asset, result[0])
                self.assertEqual(generator.width, result[1])
                self.assertEqual(generator.height, result[2])

                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

    """
    🔽🔽🔽 _get_asset_url with preview
    """

    def test__get_asset_url__with_preview(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        asset = {"preview": self.bc.fake.url()}
        model = self.bc.database.create(asset=asset)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        urls = ["", self.bc.fake.url()]

        for url in urls:
            for args, result in constructor_cases:
                generator = AssetThumbnailGenerator(*args)
                with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": url}))):
                    default_url = generator._get_asset_url()

                self.assertEqual(default_url, model.asset.preview)
                self.assertEqual(generator.asset, result[0])
                self.assertEqual(generator.width, result[1])
                self.assertEqual(generator.height, result[2])

                self.assertEqual(
                    self.bc.database.list_of("registry.Asset"),
                    [
                        self.bc.format.to_dict(model.asset),
                    ],
                )

    """
    🔽🔽🔽 _get_media without media
    """

    def test__get_media__without_media(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1, asset_category=1, academy=1)
        constructor_cases = [
            ((None,), (None, 0, 0)),
            ((None, 0, 0), (None, 0, 0)),
            ((None, width, 0), (None, width, 0)),
            ((None, 0, height), (None, 0, height)),
            ((None, width, height), (None, width, height)),
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media()

            self.assertEqual(media, None)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media with media, slug don't match
    """

    def test__get_media__with_media__slug_does_not_match(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1, media=1, academy=1)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media()

            self.assertEqual(media, None)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media with media, slug match
    """

    def test__get_media__with_media__slug_match(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        academy_slug = self.bc.fake.slug()
        asset_slug = self.bc.fake.slug()
        asset = {"slug": asset_slug}
        asset_category_slug = "default"
        asset_category = {"slug": asset_category_slug}
        media = {"slug": f"{academy_slug}-{asset_category_slug}-{asset_slug}"}
        academy = {"slug": academy_slug}
        model = self.bc.database.create(asset=asset, media=media, asset_category=asset_category, academy=academy)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media()

            self.assertEqual(media, model.media)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media_resolution with media, without MediaResolution
    """

    def test__get_media_resolution__with_media__without_media_resolution(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        slug = self.bc.fake.slug()
        asset = {"slug": slug}
        media = {"slug": f"asset-{slug}"}
        model = self.bc.database.create(asset=asset, media=media)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media_resolution(model.media.hash)

            self.assertEqual(media, None)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media_resolution with media, with MediaResolution, hash don't match
    """

    def test__get_media_resolution__with_media__with_media_resolution__hash_does_not_match(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        slug = self.bc.fake.slug()
        asset = {"slug": slug}
        media = {"slug": f"asset-{slug}"}
        model = self.bc.database.create(asset=asset, media=media, media_resolution=1)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media_resolution(model.media.hash)

            self.assertEqual(media, None)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media_resolution with media, with MediaResolution, hash match, resolution don't match
    """

    def test__get_media_resolution__with_media__with_media_resolution__hash_match__resolution_does_not_match(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        slug = self.bc.fake.slug()
        hash = self.bc.fake.slug()
        asset = {"slug": slug}
        media = {"slug": f"asset-{slug}", "hash": hash}
        media_resolution = {"hash": hash}
        model = self.bc.database.create(asset=asset, media=media, media_resolution=media_resolution)
        constructor_cases = [
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media_resolution(model.media.hash)

            self.assertEqual(media, None)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _get_media_resolution with media, with MediaResolution, hash match, resolution match
    """

    def test__get_media_resolution__with_media__with_media_resolution__hash_match__resolution_match(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        slug = self.bc.fake.slug()
        hash = self.bc.fake.slug()
        asset = {"slug": slug}
        media = {"slug": f"asset-{slug}", "hash": hash}
        model = self.bc.database.create(asset=asset, media=media)
        constructor_cases = [
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in constructor_cases:
            media_resolution = {"hash": hash, "width": width, "height": height}
            model2 = self.bc.database.create(media_resolution=media_resolution)
            generator = AssetThumbnailGenerator(*args)
            media = generator._get_media_resolution(model.media.hash)

            self.assertEqual(media, model2.media_resolution)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

            # teardown
            self.bc.database.delete("media.MediaResolution")

    """
    🔽🔽🔽 _the_client_want_resize returns False
    """

    def test__the_client_want_resize__return_false(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1)
        cases = [
            ((None,), (None, 0, 0)),
            ((None, 0, 0), (None, 0, 0)),
            ((None, width, height), (None, width, height)),
            ((model.asset,), (model.asset, 0, 0)),
            ((model.asset, 0, 0), (model.asset, 0, 0)),
            ((model.asset, width, height), (model.asset, width, height)),
        ]

        for args, result in cases:
            generator = AssetThumbnailGenerator(*args)
            will_be_resized = generator._the_client_want_resize()

            self.assertEqual(will_be_resized, False)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 _the_client_want_resize returns True
    """

    def test__the_client_want_resize__return_true(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        model = self.bc.database.create(asset=1)
        cases = [
            ((None, width, 0), (None, width, 0)),
            ((None, 0, height), (None, 0, height)),
            ((model.asset, width, 0), (model.asset, width, 0)),
            ((model.asset, 0, height), (model.asset, 0, height)),
        ]

        for args, result in cases:
            generator = AssetThumbnailGenerator(*args)
            will_be_resized = generator._the_client_want_resize()

            self.assertEqual(will_be_resized, True)
            self.assertEqual(generator.asset, result[0])
            self.assertEqual(generator.width, result[1])
            self.assertEqual(generator.height, result[2])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

    """
    🔽🔽🔽 get_thumbnail_url without Asset, returns default url, permanent is False
    """

    @patch("breathecode.registry.tasks.async_create_asset_thumbnail.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_create_asset_thumbnail_legacy.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_resize_asset_thumbnail.delay", MagicMock())
    def test__get_thumbnail_url__without_asset(self):
        generator = AssetThumbnailGenerator(None)
        default_url = self.bc.fake.url()
        with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": default_url}))):
            url = generator.get_thumbnail_url()

        self.assertEqual(url, (default_url, False))
        self.assertEqual(generator.asset, None)
        self.assertEqual(generator.width, 0)
        self.assertEqual(generator.height, 0)

        self.assertEqual(self.bc.database.list_of("registry.Asset"), [])
        self.assertEqual(self.bc.database.list_of("media.Media"), [])
        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])

        self.assertEqual(tasks.async_create_asset_thumbnail.delay.call_args_list, [])
        self.assertEqual(tasks.async_create_asset_thumbnail_legacy.delay.call_args_list, [])
        self.assertEqual(tasks.async_resize_asset_thumbnail.delay.call_args_list, [])

    """
    🔽🔽🔽 get_thumbnail_url with Asset, returns default url, permanent is False
    """

    @patch("breathecode.registry.tasks.async_create_asset_thumbnail.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_create_asset_thumbnail_legacy.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_resize_asset_thumbnail.delay", MagicMock())
    def test__get_thumbnail_url__with_asset(self):
        model = self.bc.database.create(asset=1, academy=1, asset_category=1)
        generator = AssetThumbnailGenerator(model.asset)
        default_url = self.bc.fake.url()
        with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": default_url}))):
            url = generator.get_thumbnail_url()

        self.assertEqual(url, (default_url, False))
        self.assertEqual(generator.asset, model.asset)
        self.assertEqual(generator.width, 0)
        self.assertEqual(generator.height, 0)

        self.assertEqual(
            self.bc.database.list_of("registry.Asset"),
            [
                self.bc.format.to_dict(model.asset),
            ],
        )

        self.assertEqual(self.bc.database.list_of("media.Media"), [])
        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])

        self.assertEqual(
            tasks.async_create_asset_thumbnail.delay.call_args_list,
            [
                call(model.asset.slug),
            ],
        )
        self.assertEqual(tasks.async_create_asset_thumbnail_legacy.delay.call_args_list, [])
        self.assertEqual(tasks.async_resize_asset_thumbnail.delay.call_args_list, [])

    """
    🔽🔽🔽 get_thumbnail_url with Asset and Media, slug don't match, returns default url, permanent is False
    """

    @patch("breathecode.registry.tasks.async_create_asset_thumbnail.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_create_asset_thumbnail_legacy.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_resize_asset_thumbnail.delay", MagicMock())
    def test__get_thumbnail_url__with_asset__with_media__slug_does_not_match(self):
        model = self.bc.database.create(asset=1, media=1, academy=1)
        generator = AssetThumbnailGenerator(model.asset)
        default_url = self.bc.fake.url()
        with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": default_url}))):
            url = generator.get_thumbnail_url()

        self.assertEqual(url, (default_url, False))
        self.assertEqual(generator.asset, model.asset)
        self.assertEqual(generator.width, 0)
        self.assertEqual(generator.height, 0)

        self.assertEqual(
            self.bc.database.list_of("registry.Asset"),
            [
                self.bc.format.to_dict(model.asset),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("media.Media"),
            [
                self.bc.format.to_dict(model.media),
            ],
        )

        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])

        self.assertEqual(tasks.async_create_asset_thumbnail.delay.call_args_list, [call(model.asset.slug)])
        self.assertEqual(tasks.async_create_asset_thumbnail_legacy.delay.call_args_list, [])
        self.assertEqual(tasks.async_resize_asset_thumbnail.delay.call_args_list, [])

    """
    🔽🔽🔽 get_thumbnail_url with Asset and Media, slug match, returns default url, permanent is True
    """

    @patch("breathecode.registry.tasks.async_create_asset_thumbnail.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_create_asset_thumbnail_legacy.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_resize_asset_thumbnail.delay", MagicMock())
    def test__get_thumbnail_url__with_asset__with_media__slug_match(self):
        academy_slug = self.bc.fake.slug()
        asset_slug = self.bc.fake.slug()
        asset = {"slug": asset_slug}
        asset_category_slug = "default"
        asset_category = {"slug": asset_category_slug}
        media = {"slug": f"{academy_slug}-{asset_category_slug}-{asset_slug}"}
        academy = {"slug": academy_slug}
        model = self.bc.database.create(asset=asset, media=media, asset_category=asset_category, academy=academy)
        generator = AssetThumbnailGenerator(model.asset)
        default_url = self.bc.fake.url()

        with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": default_url}))):
            url = generator.get_thumbnail_url()

        self.assertEqual(generator.asset, model.asset)
        self.assertEqual(generator.width, 0)
        self.assertEqual(generator.height, 0)

        self.assertEqual(
            self.bc.database.list_of("registry.Asset"),
            [
                self.bc.format.to_dict(model.asset),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("media.Media"),
            [
                {
                    **self.bc.format.to_dict(model.media),
                    "hits": 1,
                }
            ],
        )

        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])

        self.assertEqual(tasks.async_create_asset_thumbnail.delay.call_args_list, [])
        self.assertEqual(tasks.async_create_asset_thumbnail_legacy.delay.call_args_list, [])
        self.assertEqual(tasks.async_resize_asset_thumbnail.delay.call_args_list, [])

    """
    🔽🔽🔽 get_thumbnail_url with Asset and Media, with MediaResolution, passing width or height slug match,
    returns default url, permanent is True
    """

    @patch("breathecode.registry.tasks.async_create_asset_thumbnail.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_create_asset_thumbnail_legacy.delay", MagicMock())
    @patch("breathecode.registry.tasks.async_resize_asset_thumbnail.delay", MagicMock())
    def test__get_thumbnail_url__with_asset__with_media__with_media_resolution__passing_width_or_height(self):
        width = randint(1, 2000)
        height = randint(1, 2000)
        hash = self.bc.fake.slug()
        asset_slug = self.bc.fake.slug()
        asset = {"slug": asset_slug}
        asset_category_slug = self.bc.fake.slug()
        asset_category = {"slug": asset_category_slug}
        academy_slug = self.bc.fake.slug()
        academy = {"slug": academy_slug}
        media = {"slug": f"{academy_slug}-{asset_category_slug}-{asset_slug}", "hash": hash}
        media_resolution = {"hash": hash, "width": width, "height": height}

        model = self.bc.database.create(
            asset=asset, media=media, media_resolution=media_resolution, asset_category=asset_category, academy=academy
        )

        cases = [((model.asset, width, 0), (width, 0, 1)), ((model.asset, 0, height), (0, height, 2))]

        for args, result in cases:
            generator = AssetThumbnailGenerator(*args)
            default_url = self.bc.fake.url()

            with patch("os.getenv", MagicMock(side_effect=apply_get_env({"DEFAULT_ASSET_PREVIEW_URL": default_url}))):
                url = generator.get_thumbnail_url()

            self.assertEqual(generator.asset, model.asset)
            self.assertEqual(generator.width, result[0])
            self.assertEqual(generator.height, result[1])

            self.assertEqual(
                self.bc.database.list_of("registry.Asset"),
                [
                    self.bc.format.to_dict(model.asset),
                ],
            )

            self.assertEqual(
                self.bc.database.list_of("media.Media"),
                [
                    self.bc.format.to_dict(model.media),
                ],
            )

            self.assertEqual(tasks.async_create_asset_thumbnail.delay.call_args_list, [])
            self.assertEqual(tasks.async_create_asset_thumbnail_legacy.delay.call_args_list, [])
            self.assertEqual(tasks.async_resize_asset_thumbnail.delay.call_args_list, [])
