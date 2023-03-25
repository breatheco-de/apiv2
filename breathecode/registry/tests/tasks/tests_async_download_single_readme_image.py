"""
Test async_download_single_readme_image
"""
from random import randint
from unittest.mock import MagicMock, call, patch, PropertyMock

from breathecode.registry.tasks import async_download_single_readme_image
from logging import Logger
from breathecode.tests.mocks import apply_requests_get_mock
from ..mixins import RegistryTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


original_url = 'https://www.google.com'


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET with status not ok
    """

    @patch('requests.get',
           apply_requests_get_mock([(
               200,
               original_url,
               {
                   'headers': {
                       'content-type': 'image/png'
                   }
               },
           )]))
    def test__with_wrong_file_format(self):
        asset_image = {'name': 'john', 'original_url': original_url, 'bucket_url': 'https://www.f.com'}
        model = self.bc.database.create(asset={'slug': 'fake_slug'}, asset_image=asset_image)

        result = async_download_single_readme_image('fake_slug', 'https://www.f.com')
        asset_image = self.bc.database.get_model('registry.AssetImage').objects.first()

        self.assertEqual(result, False)
        self.assertEqual(
            asset_image.download_details,
            f'Skipping image download for {original_url} in asset fake_slug, invalid mime application/json')

    @patch('requests.get',
           apply_requests_get_mock([(200, original_url, {
               'headers': {
                   'content-type': 'image/png'
               }
           }, {
               'content-type': 'image/png'
           })]))
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(side_effect=[None, 1]),
                    upload=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({
               'GOOGLE_PROJECT_ID': 'labor-day-story',
               'MEDIA_GALLERY_BUCKET': 'bucket-name',
           })))
    def test__with_download_status_no_asset_image(self):
        model = self.bc.database.create(asset={'slug': 'fake_slug'})

        result = async_download_single_readme_image('fake_slug', original_url)

        readme = self.bc.database.get_model('registry.asset').objects.first().get_readme()['decoded']
        asset_image = self.bc.database.get_model('registry.AssetImage').objects.first()
        self.assertEqual(result, 'OK')
        self.assertEqual('https://xyz/hardcoded_url' in readme, False)
        self.assertEqual(self.bc.database.list_of('registry.AssetImage'), [{
            'id': 1,
            'bucket_url': 'https://xyz/hardcoded_url',
            'original_url': original_url,
            'download_details': f'Downloading {original_url}',
            'download_status': 'OK',
            'hash': asset_image.hash,
            'last_download_at': asset_image.last_download_at,
            'mime': 'image/png',
            'name': 'www.google.com',
        }])

    @patch('requests.get',
           apply_requests_get_mock([(200, original_url, {
               'headers': {
                   'content-type': 'image/png'
               }
           }, {
               'content-type': 'image/png'
           })]))
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    blob=PropertyMock(side_effect=[None, 1]),
                    upload=MagicMock(),
                    url=MagicMock(return_value='https://xyz/hardcoded_url'),
                    create=True)
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
        asset_image = self.bc.database.get_model('registry.AssetImage').objects.first()
        self.assertEqual(result, 'OK')
        self.assertEqual('https://xyz/hardcoded_url' in readme, True)
        self.assertEqual(self.bc.database.list_of('registry.AssetImage'), [{
            'id': 1,
            'bucket_url': 'https://xyz/hardcoded_url',
            'original_url': original_url,
            'download_details': 'Downloading https://www.f.com',
            'download_status': 'OK',
            'hash': asset_image.hash,
            'last_download_at': None,
            'mime': 'image/png',
            'name': 'john',
        }])

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
