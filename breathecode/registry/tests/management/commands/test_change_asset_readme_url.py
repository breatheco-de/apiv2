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
    def test_change_asset_readme_url_without_readme(self):
        from django.core.management.base import OutputWrapper

        # model = self.bc.database.create(readme_url='https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md')

        command = Command()

        result = command.handle()

        self.assertEqual(result, None)

        self.assertEqual(OutputWrapper.write.call_count, 0)

        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

        self.assertEqual(OutputWrapper.write.call_args_list, [])

    # @patch('django.core.management.base.OutputWrapper.write', MagicMock())
    # def test_change_asset_readme_url(self):
    #     """
    #     Descriptions of models are being generated:

    #       Academy(id=1):
    #         city: City(id=1)
    #         country: Country(code="UgN")

    #       Cohort(id=1):
    #         academy: Academy(id=1)
    #         schedule: SyllabusSchedule(id=1)

    #       SyllabusSchedule(id=1):
    #         academy: Academy(id=1)
    #     """
    #     from django.core.management.base import OutputWrapper

    #     readme = [{
    #         'readme_url':
    #         'https://raw.githubusercontent.com/breatheco-de/exercise-postcard/main/README.md'
    #     }]

    #     model = self.bc.database.create(asset=readme)

    #     command = Command()

    #     result = command.handle()

    #     self.assertEqual(result, None)

    #     #self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

    #     self.assertEqual(self.bc.database.list_of('registry.Asset'), [
    #         {
    #             **self.bc.format.to_dict(model.asset),
    #             'readme_url':
    #             'https://github.com/breatheco-de/exercise-postcard/blob/main/README.md',
    #         },
    #     ])
    #     self.assertEqual(OutputWrapper.write.call_args_list, [call('Done!')])
