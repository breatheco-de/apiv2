"""
Test async_download_single_readme_image
"""

import base64
from unittest.mock import MagicMock, patch, PropertyMock

from breathecode.registry.tasks import async_download_single_readme_image
from breathecode.tests.mixins.legacy import LegacyAPITestCase
from breathecode.tests.mocks import apply_requests_get_mock
from django.utils import timezone

UTC_NOW = timezone.now()


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


original_url = "https://www.google.com"


class TestRegistry(LegacyAPITestCase):
    """
    🔽🔽🔽 GET with status not ok
    """

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [
                (
                    200,
                    original_url,
                    {"headers": {"content-type": "image/png"}},
                )
            ]
        ),
    )
    def test__with_wrong_file_format(self):
        asset_image = {"name": "john", "original_url": original_url, "bucket_url": "https://www.f.com"}
        model = self.bc.database.create(asset={"slug": "fake_slug"}, asset_image=asset_image)

        bc = self.bc.format.to_dict(model.asset_image)
        async_download_single_readme_image.delay("fake_slug", "https://www.f.com")

        self.bc.database.list_of("registry.AssetImage"), [
            {
                **bc,
                "download_details": f"Skipping image download for {original_url} in asset fake_slug, invalid mime application/json",
                "download_status": "ERROR",
            }
        ]

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [(200, original_url, {"headers": {"content-type": "image/png"}}, {"content-type": "image/png"})]
        ),
    )
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test__with_download_status_no_asset_image(self):
        model = self.bc.database.create(asset={"slug": "fake_slug"})

        async_download_single_readme_image.delay("fake_slug", original_url)
        # The content is static in the decorator, so the hash is always the same
        hash = "5186bd77843e507d2c6f568d282c56b06622b2fc7d6ae6a109c97ee1fc3cdebc"

        readme = self.bc.database.get_model("registry.asset").objects.first().get_readme()["decoded"]

        self.assertEqual("https://xyz/hardcoded_url" in readme, False)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetImage"),
            [
                {
                    "id": 1,
                    "bucket_url": "https://xyz/hardcoded_url",
                    "original_url": original_url,
                    "download_details": f"Downloading {original_url}",
                    "download_status": "OK",
                    "hash": hash,
                    "last_download_at": UTC_NOW,
                    "mime": "image/png",
                    "name": "www.google.com",
                }
            ],
        )

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [(200, original_url, {"headers": {"content-type": "image/png"}}, {"content-type": "image/png"})]
        ),
    )
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test__with_download_status_not_ok(self):
        asset_image = {"name": "john", "original_url": original_url, "bucket_url": "https://www.f.com"}
        start_of_readme = "hi "
        fake_readme = f"{start_of_readme}https://www.f.com"
        encoded_readme = base64.b64encode(fake_readme.encode("utf-8")).decode("utf-8")

        model = self.bc.database.create(
            asset={"slug": "fake_slug", "readme": encoded_readme, "readme_raw": encoded_readme}, asset_image=asset_image
        )
        # store the original readme_raw to verify it does not get modified
        readme_raw = model["asset"].readme_raw

        asset = self.bc.format.to_dict(model.asset)
        async_download_single_readme_image.delay("fake_slug", "https://www.f.com")
        # The content is static in the decorator, so the hash is always the same
        hash = "5186bd77843e507d2c6f568d282c56b06622b2fc7d6ae6a109c97ee1fc3cdebc"

        readme = self.bc.database.get_model("registry.asset").objects.first().get_readme()["decoded"]
        asset_image = self.bc.database.get_model("registry.AssetImage").objects.first()
        self.bc.database.list_of("registry.Asset"), [
            {
                **asset,
                "readme_raw": readme_raw,
            }
        ]
        self.assertEqual(readme.count("https://xyz/hardcoded_url"), 1)
        self.assertEqual(start_of_readme in readme, True)
        self.assertEqual("https://www.f.com" not in readme, True)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetImage"),
            [
                {
                    "id": 1,
                    "bucket_url": "https://xyz/hardcoded_url",
                    "original_url": original_url,
                    "download_details": "Downloading https://www.f.com",
                    "download_status": "OK",
                    "hash": hash,
                    "last_download_at": None,
                    "mime": "image/png",
                    "name": "john",
                }
            ],
        )

    @patch(
        "requests.get",
        apply_requests_get_mock(
            [(200, original_url, {"headers": {"content-type": "image/png"}}, {"content-type": "image/png"})]
        ),
    )
    @patch.multiple(
        "breathecode.services.google_cloud.Storage",
        __init__=MagicMock(return_value=None),
        client=PropertyMock(),
        create=True,
    )
    @patch.multiple(
        "breathecode.services.google_cloud.File",
        __init__=MagicMock(return_value=None),
        bucket=PropertyMock(),
        file_name=PropertyMock(),
        blob=PropertyMock(side_effect=[None, 1]),
        upload=MagicMock(),
        url=MagicMock(return_value="https://xyz/hardcoded_url"),
        create=True,
    )
    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test__with_download_status_not_ok_many_images(self):
        asset_image = {"name": "john", "original_url": original_url, "bucket_url": "https://www.f.com"}
        start_of_readme = "hi "
        fake_readme = f"{start_of_readme}https://www.f.com https://www.f.com https://www.f.com"
        encoded_readme = base64.b64encode(fake_readme.encode("utf-8")).decode("utf-8")

        model = self.bc.database.create(
            asset={"slug": "fake_slug", "readme": encoded_readme, "readme_raw": encoded_readme}, asset_image=asset_image
        )

        # store the original readme_raw to verify it does not get modified
        readme_raw = model["asset"].readme_raw

        async_download_single_readme_image.delay("fake_slug", "https://www.f.com")
        # The content is static in the decorator, so the hash is always the same
        hash = "5186bd77843e507d2c6f568d282c56b06622b2fc7d6ae6a109c97ee1fc3cdebc"

        readme = self.bc.database.get_model("registry.asset").objects.first().get_readme()["decoded"]
        asset_image = self.bc.database.get_model("registry.AssetImage").objects.first()
        self.assertEqual(readme.count("https://xyz/hardcoded_url"), 3)
        self.assertEqual(start_of_readme in readme, True)
        self.assertEqual("https://www.f.com" not in readme, True)
        self.assertEqual(readme_raw, self.bc.database.get_model("registry.asset").objects.first().readme_raw)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetImage"),
            [
                {
                    "id": 1,
                    "bucket_url": "https://xyz/hardcoded_url",
                    "original_url": original_url,
                    "download_details": "Downloading https://www.f.com",
                    "download_status": "OK",
                    "hash": hash,
                    "last_download_at": None,
                    "mime": "image/png",
                    "name": "john",
                }
            ],
        )

    """
    🔽🔽🔽 GET with status ok
    """

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test__with_ok_download_status(self):
        asset_image = {"name": "john", "bucket_url": "https://www.f.com", "download_status": "OK"}
        fake_readme = "hi https://www.f.com"
        encoded_readme = base64.b64encode(fake_readme.encode("utf-8")).decode("utf-8")

        model = self.bc.database.create(
            asset={"slug": "fake_slug", "readme": encoded_readme, "readme_raw": encoded_readme}, asset_image=asset_image
        )

        # store the original readme_raw to verify it does not get modified
        readme_raw = model["asset"].readme_raw

        async_download_single_readme_image.delay("fake_slug", "https://www.f.com")

        readme = self.bc.database.get_model("registry.asset").objects.first().get_readme()["decoded"]

        self.assertEqual(readme_raw, self.bc.database.get_model("registry.asset").objects.first().readme_raw)
        self.assertEqual(fake_readme, readme)
