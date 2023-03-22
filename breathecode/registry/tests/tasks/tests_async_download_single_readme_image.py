"""
Test async_download_single_readme_image
"""
from random import randint
from unittest.mock import MagicMock, call, patch

from breathecode.registry.tasks import async_download_single_readme_image
from logging import Logger
from ..mixins import RegistryTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET without Media
    """

    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'GOOGLE_PROJECT_ID': 'labor-day-story',
               'MEDIA_GALLERY_BUCKET': 'bucket-name',
           })))
    def test__with_asset(self):
        asset_image = {'name': 'john', 'bucket_url': 'https://www.f.com', 'download_status': 'OK'}
        model = self.bc.database.create(asset={'slug': 'fake_slug'}, asset_image=asset_image)

        readme = model['asset'].get_readme()
        model['asset'].set_readme(readme['decoded'] + ' https://www.f.com')
        model['asset'].save()

        result = async_download_single_readme_image('fake_slug', 'https://www.f.com')

        readme = self.bc.database.get_model('registry.asset').objects.first().get_readme()['decoded']

        self.assertEqual(result, 'OK')
        self.assertEqual('https://www.f.com' in readme, True)
