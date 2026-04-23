"""
Test /answer
"""

from random import randint
from unittest.mock import MagicMock, call, patch
from breathecode.registry import tasks

from breathecode.registry.models import Asset
from breathecode.registry.actions import clean_readme_hide_comments, clean_readme_relative_paths, clean_asset_readme
from ..mixins import RegistryTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Clean readme content in several ways
    """

    def test__hide_comments(self):
        original_content = """For example, we need the following application URLs to match the following components:
<!-- hide -->
![react router](../../assets/images/6fd2b44b-598b-4ddb-85ba-9c32b086127f.png)
<!-- endhide -->
## Defining your Application Routes"""

        model = self.bc.database.create(
            asset={
                "readme_url": "https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md",
                "readme_raw": Asset.encode(original_content),
                "readme": Asset.encode(original_content),
            }
        )

        asset = clean_readme_hide_comments(model["asset"])
        readme = asset.get_readme()
        self.assertEqual(asset.readme_raw, Asset.encode(original_content))
        self.assertEqual(
            readme["decoded"],
            """For example, we need the following application URLs to match the following components:

## Defining your Application Routes""",
        )

    def test__relative_paths(self):

        original_content = Asset.encode(
            """For example, we need the following application URLs to match the following components:

![react router](../../assets/images/6fd2b44b-598b-4ddb-85ba-9c32b086127f.png)

## Defining your Application Routes"""
        )

        model = self.bc.database.create(
            asset={
                "readme_url": "https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md",
                "readme_raw": original_content,
                "readme": original_content,
            }
        )

        asset = clean_readme_relative_paths(model["asset"])
        readme = asset.get_readme()

        self.assertEqual(asset.readme_raw, original_content)
        self.assertEqual(
            readme["decoded"],
            """For example, we need the following application URLs to match the following components:

![react router](https://github.com/breatheco-de/content/blob/master/src/content/lesson/../../assets/images/6fd2b44b-598b-4ddb-85ba-9c32b086127f.png?raw=true)

## Defining your Application Routes""",
        )

    def test__clean_asset(self):

        original_content = Asset.encode(
            """For example, we need the following application URLs to match the following components:
<!-- hide -->
i should hide
<!-- endhide -->
![react router](../../assets/images/6fd2b44b-598b-4ddb-85ba-9c32b086127f.png)

## Defining your Application Routes"""
        )

        model = self.bc.database.create(
            asset={
                "readme_url": "https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md",
                "readme_raw": original_content,
                "readme": original_content,
            }
        )

        asset = clean_asset_readme(model["asset"])

        self.assertEqual(asset.readme_raw, original_content)
        self.assertEqual(
            asset.readme,
            Asset.encode(
                """For example, we need the following application URLs to match the following components:

![react router](https://github.com/breatheco-de/content/blob/master/src/content/lesson/../../assets/images/6fd2b44b-598b-4ddb-85ba-9c32b086127f.png?raw=true)

## Defining your Application Routes"""
            ),
        )

    def test__clean_asset_without_readme_raw(self):
        model = self.bc.database.create(
            asset={
                "readme_url": "https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md",
            }
        )

        asset = clean_asset_readme(model["asset"])
        self.assertEqual(asset, model["asset"])

    def test__clean_asset_adds_canonical_telemetry_batch_for_interactive_assets(self):
        readme_content = Asset.encode("# Hello")
        model = self.bc.database.create(
            asset=[
                {
                    "slug": "telemetry-us",
                    "lang": "us",
                    "interactive": True,
                    "readme_url": "https://github.com/org/repo/blob/main/README.md",
                    "readme_raw": readme_content,
                    "readme": readme_content,
                },
                {
                    "slug": "telemetry-es",
                    "lang": "es",
                    "interactive": True,
                    "readme_url": "https://github.com/org/repo/blob/main/README.es.md",
                    "readme_raw": readme_content,
                    "readme": readme_content,
                },
            ]
        )
        canonical = model["asset"][0]
        translated = model["asset"][1]
        translated.all_translations.add(canonical)

        cleaned = clean_asset_readme(translated)
        expected = f"https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id={canonical.id}"
        self.assertEqual(cleaned.config["telemetry"]["batch"], expected)

    def test__clean_asset_overwrites_wrong_telemetry_batch_for_interactive_assets(self):
        readme_content = Asset.encode("# Hello")
        model = self.bc.database.create(
            asset={
                "slug": "telemetry-wrong",
                "lang": "us",
                "interactive": True,
                "config": {"telemetry": {"batch": "https://wrong/url?asset_id=999"}},
                "readme_url": "https://github.com/org/repo/blob/main/README.md",
                "readme_raw": readme_content,
                "readme": readme_content,
            }
        )
        asset = model["asset"]

        cleaned = clean_asset_readme(asset)
        expected = f"https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id={asset.id}"
        self.assertEqual(cleaned.config["telemetry"]["batch"], expected)

    def test__clean_asset_non_interactive_keeps_config_unchanged(self):
        readme_content = Asset.encode("# Hello")
        original_config = {"delivery": {"formats": ["url"]}}
        model = self.bc.database.create(
            asset={
                "slug": "telemetry-noop",
                "lang": "us",
                "interactive": False,
                "config": original_config,
                "readme_url": "https://github.com/org/repo/blob/main/README.md",
                "readme_raw": readme_content,
                "readme": readme_content,
            }
        )

        cleaned = clean_asset_readme(model["asset"])
        self.assertEqual(cleaned.config, original_config)
