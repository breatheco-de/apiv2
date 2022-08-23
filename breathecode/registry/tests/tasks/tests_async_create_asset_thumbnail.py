"""
Test /answer
"""
from random import randint
from unittest.mock import MagicMock, PropertyMock, call, patch

from breathecode.registry.tasks import async_create_asset_thumbnail
from logging import Logger
from breathecode.services.google_cloud.function_v1 import FunctionV1

from breathecode.tests.mixins.breathecode_mixin.breathecode import fake
from ..mixins import RegistryTestCase


class Response:

    def __init__(self, response, status_code):
        self.response = response
        self.status_code = status_code

    def json(self):
        return self.response


WIDTH = randint(0, 2000)
HEIGHT = randint(0, 2000)
URL = fake.url()
FUNCTION_GOOD_RESPONSE = Response([{
    'url': URL,
    'filename': 'xyz.png',
}], 200)
FUNCTION_BAD_RESPONSE = Response({'status_code': 400, 'message': 'Bad response'}, 400)


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Without Asset
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test__without_asset(self):
        async_create_asset_thumbnail.delay('slug')

        self.assertEqual(self.bc.database.list_of('media.Media'), [])
        self.assertEqual(Logger.warn.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [call('Asset with slug slug not found')])

    """
    🔽🔽🔽 With Asset, bad Function response
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.__init__', MagicMock(return_value=None))
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.call',
           MagicMock(return_value=FUNCTION_BAD_RESPONSE))
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    def test__with_asset__bad_function_response(self):
        model = self.bc.database.create(asset=1)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [])
        self.assertEqual(Logger.warn.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [
            call('Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` '
                 'returns status code 400'),
        ])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(
                    params={
                        'url': f'https://4geeksacademy.com/us/learn-to-code/{model.asset.slug}/preview',
                        'name': f'learn-to-code-{model.asset.slug}.png',
                        'dimension': '1200x630',
                        'delay': 1000,
                    })
            ]))

    """
    🔽🔽🔽 With Asset, good Function response
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.__init__', MagicMock(return_value=None))
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.call',
           MagicMock(return_value=FUNCTION_GOOD_RESPONSE))
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    bucket=PropertyMock(),
                    file_name=PropertyMock(),
                    delete=MagicMock(),
                    download=MagicMock(return_value=bytes('qwerty', 'utf-8')),
                    url=MagicMock(return_value='https://uio.io/path'),
                    create=True)
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    def test__with_asset__good_function_response(self):
        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        model = self.bc.database.create(asset=1)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [{
            'academy_id': None,
            'hash': hash,
            'hits': 0,
            'id': 1,
            'mime': 'image/png',
            'name': f'learn-to-code-{model.asset.slug}.png',
            'slug': f'asset-{model.asset.slug}',
            'thumbnail': 'https://uio.io/path-thumbnail',
            'url': 'https://uio.io/path',
        }])
        self.assertEqual(Logger.warn.call_args_list, [
            call(f'Media was save with {hash} for academy {model.asset.academy}'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(
                    params={
                        'url': f'https://4geeksacademy.com/us/learn-to-code/{model.asset.slug}/preview',
                        'name': f'learn-to-code-{model.asset.slug}.png',
                        'dimension': '1200x630',
                        'delay': 1000,
                    })
            ]))

    """
    🔽🔽🔽 With Asset and Media, good Function response
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.__init__', MagicMock(return_value=None))
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.call',
           MagicMock(return_value=FUNCTION_GOOD_RESPONSE))
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    delete=MagicMock(),
                    download=MagicMock(return_value=bytes('qwerty', 'utf-8')),
                    create=True)
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    def test__with_asset__with_media(self):
        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        media = {'hash': hash}
        model = self.bc.database.create(asset=1, media=media)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [
            self.bc.format.to_dict(model.media),
        ])
        self.assertEqual(Logger.warn.call_args_list, [
            call(f'Media with hash {hash} already exists, skipping'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(
                    params={
                        'url': f'https://4geeksacademy.com/us/learn-to-code/{model.asset.slug}/preview',
                        'name': f'learn-to-code-{model.asset.slug}.png',
                        'dimension': '1200x630',
                        'delay': 1000,
                    })
            ]))

    """
    🔽🔽🔽 With Asset and Media, good Function response, Media for another Academy
    """

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.__init__', MagicMock(return_value=None))
    @patch('breathecode.services.google_cloud.function_v1.FunctionV1.call',
           MagicMock(return_value=FUNCTION_GOOD_RESPONSE))
    @patch.multiple('breathecode.services.google_cloud.Storage',
                    __init__=MagicMock(return_value=None),
                    client=PropertyMock(),
                    create=True)
    @patch.multiple('breathecode.services.google_cloud.File',
                    __init__=MagicMock(return_value=None),
                    delete=MagicMock(),
                    download=MagicMock(return_value=bytes('qwerty', 'utf-8')),
                    create=True)
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    def test__with_asset__with_media__media_for_another_academy(self):
        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        asset = {'academy_id': 1}
        media = {'hash': hash, 'academy_id': 2}
        model = self.bc.database.create(asset=asset, media=media, academy=2)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [
            self.bc.format.to_dict(model.media), {
                **self.bc.format.to_dict(model.media),
                'id': 2,
                'academy_id': 1,
                'slug': f'asset-{model.asset.slug}',
            }
        ])
        self.assertEqual(Logger.warn.call_args_list, [
            call(f'Media was save with {hash} for academy {model.academy[0]}'),
        ])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(
                    params={
                        'url': f'https://4geeksacademy.com/us/learn-to-code/{model.asset.slug}/preview',
                        'name': f'learn-to-code-{model.asset.slug}.png',
                        'dimension': '1200x630',
                        'delay': 1000,
                    })
            ]))
