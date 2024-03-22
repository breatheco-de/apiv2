"""
Test /answer
"""
from logging import Logger
from random import randint
from unittest.mock import MagicMock, PropertyMock, call, patch
from io import BytesIO

from breathecode.registry.tasks import async_create_asset_thumbnail
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

fake_file_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\t\x08\n\n\t\x08\t\t\n\x0c\x0f\x0c\n\x0b\x0e\x0b\t\t\r\x11\r\x0e\x0f\x10\x10\x11\x10\n\x0c\x12\x13\x12\x10\x13\x0f\x10\x10\x10\xff\xdb\x00C\x01\x03\x03\x03\x04\x03\x04\x08\x04\x04\x08\x10\x0b\t\x0b\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\xff\xc0\x00\x11\x08\x02v\x04\xb0\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1e\x00\x01\x00\x02\x02\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x04\x07\x03\x08\t\x02\x01\n\xff\xc4\x00i\x10\x00\x00\x06\x01\x03\x01\x03\x04\x08\r\x11\x07\x03\x01\x00\x13\x00\x01\x02\x03\x04\x05\x06\x07\x11\x12!\x08\x13\x14\t"1A\x15\x162QT\x93\xa1\xd2\x17\x18#SVWatu\x81\x95\xb4\xd3345678BCRqv\x94\xa5\xb1\xb3\xb5\xc19b\x83\x91\xb2\xd1\xd4$rs%\x19&\x82\x92Dchw\x97\xa4\xc3\xd5\xa3\xa6\xc4\xe1\xe4\xf0\xf1\xff\xc4\x00\x1c\x01\x01\x00\x02\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x04\x01\x02\x05\x06\x07\x08\xff\xc4\x00R\x11\x00\x02\x01\x02\x04\x02\x04\x08\t\x0b\x03\x02\x04\x05\x05\x01\x00\x01\x02\x03\x11\x04\x05\x12!1A\x06\x13"Q\x142aq\x81\x91\xa1\xd1\x15\x165RTs\x93\xb1\xd2#34BSr\x92\xb2\xb3\xc1\xd3\x07\xa2\xf0\x17\xe1$b\x82\xf1%Cc\xa3\xe2\x08D\x95\xc2\xd4\x83\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf5L\x00\x00\x00\x00\x00\x00\x00~n^\xf8\x03\xf4\x00\x00\x00\x1f\x86dE\xb9\x99\x10\x03\xf7\xd2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
FUNCTION_GOOD_FILE_RESPONSE = Response(fake_file_data, 200)


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Without Asset
    """

    @patch('logging.Logger.warning', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test__without_asset(self):
        async_create_asset_thumbnail.delay('slug')

        self.assertEqual(self.bc.database.list_of('media.Media'), [])
        self.assertEqual(Logger.warning.call_args_list, [call('Asset with slug slug not found')])
        self.assertEqual(Logger.error.call_args_list, [call('Asset with slug slug not found', exc_info=True)])

    # """
    # 🔽🔽🔽 With Asset, bad Function response
    # """

    # @patch('logging.Logger.warning', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # @patch('breathecode.services.google_cloud.function_v1.FunctionV1.__init__', MagicMock(return_value=None))
    # @patch('breathecode.services.google_cloud.function_v1.FunctionV1.call',
    #        MagicMock(return_value=FUNCTION_BAD_RESPONSE))
    # @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    # def test__with_asset__bad_function_response(self):
    #     asset_category = {'preview_generation_url': self.bc.fake.url()}
    #     model = self.bc.database.create_v2(asset=1, asset_category=asset_category, academy=1)
    #     async_create_asset_thumbnail.delay(model.asset.slug)

    #     self.assertEqual(self.bc.database.list_of('media.Media'), [])
    #     self.assertEqual(Logger.warning.call_args_list, [])
    #     print('Logger.error.call_args_list')
    #     print(Logger.error.call_args_list)
    #     self.assertEqual(Logger.error.call_args_list, [
    #         call(
    #             'Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` '
    #             'returns status code 400',
    #             exc_info=True),
    #     ])
    #     self.assertEqual(
    #         str(FunctionV1.__init__.call_args_list),
    #         str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
    #     self.assertEqual(
    #         str(FunctionV1.call.call_args_list),
    #         str([
    #             call(params={
    #                 'url': model.asset_category.preview_generation_url + '?slug=' + model.asset.slug,
    #                 'name': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png',
    #                 'dimension': '1200x630',
    #                 'delay': 1000,
    #             },
    #                  timeout=8)
    #         ]))
    """
    🔽🔽🔽 With Asset, good Function response
    """

    @patch('logging.Logger.warning', MagicMock())
    @patch('breathecode.registry.actions.generate_screenshot',
           MagicMock(return_value=FUNCTION_GOOD_FILE_RESPONSE))
    @patch('logging.Logger.error', MagicMock())
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
    @patch(
        'os.getenv',
        MagicMock(side_effect=apply_get_env({
            'GOOGLE_PROJECT_ID': 'labor-day-story',
            'SCREENSHOTS_BUCKET': 'random-bucket',
            'SCREENSHOT_MACHINE_KEY': '000000'
        })))
    def test__with_asset__good_function_response(self):

        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        fake_url = self.bc.fake.url()
        print('FUNCTION_GOOD_FILE_RESPONSE')
        print(FUNCTION_GOOD_FILE_RESPONSE.response)
        asset_category = {'preview_generation_url': fake_url}
        model = self.bc.database.create_v2(asset=1, asset_category=asset_category, academy=1)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(
            self.bc.database.list_of('media.Media'),
            [{
                'academy_id': model.asset.academy.id,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png',
                'slug': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}',
                'thumbnail': f'https://storage.googleapis.com/random-bucket/{hash}-thumbnail',
                'url': f'https://storage.googleapis.com/random-bucket/{hash}',
            }])
        self.assertEqual(Logger.warning.call_args_list, [
            call(f'Media was save with {hash} for academy {model.asset.academy}'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])
        # self.assertEqual(
        #     str(FunctionV1.__init__.call_args_list),
        #     str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        # self.assertEqual(
        #     str(FunctionV1.call.call_args_list),
        #     str([
        #         call(params={
        #             'url': model.asset_category.preview_generation_url + '?slug=' + model.asset.slug,
        #             'name': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png',
        #             'dimension': '1200x630',
        #             'delay': 1000,
        #         },
        #              timeout=8)
        #     ]))

    """
    🔽🔽🔽 With Asset and Media, good Function response, without AssetCategory
    """

    @patch('logging.Logger.warning', MagicMock())
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
    def test__with_asset__with_media__without_asset_category_with_url(self):
        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        media = {'hash': hash}
        model = self.bc.database.create_v2(asset=1, media=media)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [
            self.bc.format.to_dict(model.media),
        ])
        self.assertEqual(Logger.warning.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [
            call('Not able to retrieve a preview generation', exc_info=True),
        ])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(FunctionV1.call.call_args_list, [])

    """
    🔽🔽🔽 With Asset and Media, good Function response, with AssetCategory without preview_generation_url
    """

    @patch('logging.Logger.warning', MagicMock())
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
                    rename=MagicMock(),
                    download=MagicMock(return_value=bytes('qwerty', 'utf-8')),
                    create=True)
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'GOOGLE_PROJECT_ID': 'labor-day-story'})))
    def test__with_asset__with_media__with_asset_category_with_url(self):
        hash = '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5'
        media = {'hash': hash}
        asset_category = {'preview_generation_url': self.bc.fake.url()}
        model = self.bc.database.create_v2(asset=1, media=media, asset_category=asset_category, academy=1)

        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [
            self.bc.format.to_dict(model.media),
        ])

        self.assertEqual(Logger.warning.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [
            call(f'Media with hash {hash} already exists, skipping', exc_info=True),
        ])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))

        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(params={
                    'url': model.asset_category.preview_generation_url + '?slug=' + model.asset.slug,
                    'name': f'{model.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png',
                    'dimension': '1200x630',
                    'delay': 1000,
                },
                     timeout=8)
            ]))

    """
    🔽🔽🔽 With Asset and Media, good Function response, Media for another Academy
    """

    @patch('logging.Logger.warning', MagicMock())
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
        asset_category = {'preview_generation_url': self.bc.fake.url()}
        model = self.bc.database.create(asset=asset, media=media, academy=2, asset_category=asset_category)
        async_create_asset_thumbnail.delay(model.asset.slug)

        self.assertEqual(self.bc.database.list_of('media.Media'), [
            self.bc.format.to_dict(model.media), {
                **self.bc.format.to_dict(model.media),
                'id': 2,
                'academy_id': 1,
                'slug': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}',
            }
        ])
        self.assertEqual(Logger.warning.call_args_list, [])
        self.assertEqual(Logger.error.call_args_list, [
            call(f'Media was save with {hash} for academy {model.academy[0]}', exc_info=True),
        ])
        self.assertEqual(
            str(FunctionV1.__init__.call_args_list),
            str([call(region='us-central1', project_id='labor-day-story', name='screenshots', method='GET')]))
        self.assertEqual(
            str(FunctionV1.call.call_args_list),
            str([
                call(params={
                    'url': model.asset_category.preview_generation_url + '?slug=' + model.asset.slug,
                    'name': f'{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png',
                    'dimension': '1200x630',
                    'delay': 1000,
                },
                     timeout=8)
            ]))
