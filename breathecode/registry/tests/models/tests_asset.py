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

    def test__parse(self):

        model = self.bc.database.create(
            asset={
                'readme_url':
                'https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md',
                #'readme_raw': Asset.encode(original_content),
                #'readme': Asset.encode(original_content)
            })

        asset = model.asset
        result = asset.parse({})

        self.assertEqual(result, None)
