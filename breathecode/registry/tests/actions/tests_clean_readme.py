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
