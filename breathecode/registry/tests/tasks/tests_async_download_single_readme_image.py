"""
Test async_download_single_readme_image
"""
from random import randint
from unittest.mock import MagicMock, call, patch

from breathecode.registry.tasks import async_download_single_readme_image
from logging import Logger
from breathecode.tests.mocks import apply_requests_get_mock
from ..mixins import RegistryTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class FakeRequest:

    def __init__(self, *args, **kwargs):
        self.headers = {'content-type': 'image/png'}


fake_request = FakeRequest()

original_url = 'https://www.google.com'


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET with status not ok
    """

    @patch('requests.get',
           apply_requests_get_mock([(200, original_url, {
               'headers': {
                   'content-type': 'image/png'
               }
           })]))
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'GOOGLE_PROJECT_ID': 'labor-day-story',
               'MEDIA_GALLERY_BUCKET': 'bucket-name',
           })))
    def test__with_download_status_not_ok(self):
        asset_image = {'name': 'john', 'original_url': original_url, 'bucket_url': 'https://www.f.com'}
        model = self.bc.database.create(asset={'slug': 'fake_slug'}, asset_image=asset_image)

        readme = model['asset'].get_readme()
        model['asset'].set_readme(readme['decoded'] + ' https://www.f.com')
        model['asset'].save()

        result = async_download_single_readme_image('fake_slug', 'https://www.f.com')

        readme = self.bc.database.get_model('registry.asset').objects.first().get_readme()['decoded']

        # self.assertEqual(self.bc.database.list_of('media.Media'), [])
        self.assertEqual(result, 'OK')
        self.assertEqual('https://www.f.com' in readme, True)

    """
    🔽🔽🔽 GET with status ok
    """

    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'GOOGLE_PROJECT_ID': 'labor-day-story',
               'MEDIA_GALLERY_BUCKET': 'bucket-name',
           })))
    def test__with_ok_download_status(self):
        asset_image = {'name': 'john', 'bucket_url': 'https://www.f.com', 'download_status': 'OK'}
        model = self.bc.database.create(asset={'slug': 'fake_slug'}, asset_image=asset_image)

        readme = model['asset'].get_readme()
        model['asset'].set_readme(readme['decoded'] + ' https://www.f.com')
        model['asset'].save()

        result = async_download_single_readme_image('fake_slug', 'https://www.f.com')

        readme = self.bc.database.get_model('registry.asset').objects.first().get_readme()['decoded']

        self.assertEqual(result, 'OK')
        self.assertEqual('https://www.f.com' in readme, True)
