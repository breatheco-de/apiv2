"""
Tests / Registry /asset.readme_url
"""

from unittest.mock import MagicMock, patch

from ...mixins import RegistryTestCase
from ....management.commands.change_asset_readme_url import Command


class ChangeAssetReadmeUrlTestCase(RegistryTestCase):
    """
    Tests / Registry /asset.readme_url
    """

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_change_asset_readme_url_without_readme(self):
        from django.core.management.base import OutputWrapper

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(OutputWrapper.write.call_count, 0)

        self.assertEqual(self.bc.database.list_of("registry.Asset"), [])

        self.assertEqual(OutputWrapper.write.call_args_list, [])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_change_asset_readme_url_with_readme(self):
        from django.core.management.base import OutputWrapper

        random_slug1 = self.bc.random.string(lower=True, upper=True, size=10)
        random_slug2 = self.bc.random.string(lower=True, upper=True, size=5)
        random_slug3 = self.bc.random.string(lower=True, upper=True, size=5)
        random_slug4 = self.bc.random.string(lower=True, upper=True, size=10)

        readme_url1 = (
            f"https://raw.githubusercontent.com/{random_slug1}/{random_slug2}/{random_slug3}/{random_slug4}.md"
        )
        readme_url2 = (
            f"https://raw.githubusercontent.com/{random_slug4}/{random_slug3}/{random_slug2}/{random_slug1}.md"
        )
        assets = [{"readme_url": readme_url1}, {"readme_url": readme_url2}]

        model = self.bc.database.create(asset=assets)

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(OutputWrapper.write.call_count, 0)

        self.assertEqual(
            self.bc.database.list_of("registry.Asset"),
            [
                {
                    **self.bc.format.to_dict(model.asset[0]),
                    "readme_url": f"https://github.com/{random_slug1}/{random_slug2}/blob/{random_slug3}/{random_slug4}.md",
                },
                {
                    **self.bc.format.to_dict(model.asset[1]),
                    "readme_url": f"https://github.com/{random_slug4}/{random_slug3}/blob/{random_slug2}/{random_slug1}.md",
                },
            ],
        )

        self.assertEqual(OutputWrapper.write.call_args_list, [])

    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_change_asset_readme_url_without_readmes_to_change(self):
        from django.core.management.base import OutputWrapper

        readme_url1 = self.bc.fake.url()
        readme_url2 = self.bc.fake.url()
        assets = [{"readme_url": readme_url1}, {"readme_url": readme_url2}]

        model = self.bc.database.create(asset=assets)

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(OutputWrapper.write.call_count, 0)

        self.assertEqual(
            self.bc.database.list_of("registry.Asset"),
            [
                {**self.bc.format.to_dict(model.asset[0]), "readme_url": readme_url1},
                {**self.bc.format.to_dict(model.asset[1]), "readme_url": readme_url2},
            ],
        )

        self.assertEqual(OutputWrapper.write.call_args_list, [])
