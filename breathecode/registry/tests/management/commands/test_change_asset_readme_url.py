'''
Tests / Registry /asset.readme_url
'''
from unittest.mock import MagicMock, patch, call
from mixer.backend.django import mixer

from ...mixins import RegistryTestCase
from ....management.commands.change_asset_readme_url import Command


class ChangeAssetReadmeUrlTestCase(RegistryTestCase):
    '''
    Tests / Registry /asset.readme_url
    '''

    @patch('django.core.management.base.OutputWrapper.write', MagicMock())
    def test_change_asset_readme_url(self):
        from django.core.management.base import OutputWrapper

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(OutputWrapper.write.call_args_list, [])

        self.assertEqual(OutputWrapper.write.call_count, 0)

        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])
