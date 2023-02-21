"""
Test /answer
"""
from random import randint
import random
import string
import base64
from unittest.mock import MagicMock, patch, call
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.registry.actions import AssetThumbnailGenerator
from breathecode.registry.caches import TechnologyCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import RegistryTestCase


def get_serializer(asset_technology, assets=[], asset_technologies=[]):
    return {
        'alias': asset_technologies,
        'assets': assets,
        'description': asset_technology.description,
        'icon_url': asset_technology.icon_url,
        'parent': {
            'description': asset_technology.description,
            'icon_url': asset_technology.icon_url,
            'slug': asset_technology.slug,
            'title': asset_technology.title,
        } if asset_technology.parent else None,
        'slug': asset_technology.slug,
        'title': asset_technology.title,
        'sort_priority': asset_technology.sort_priority,
    }


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_number_one(self):
        url = reverse_lazy('registry:asset_slug_extension',
                           kwargs={
                               'asset_slug': 'this_is_a_slug',
                               'extension': 'md'
                           })
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'Asset this_is_a_slug not found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

    def test_number_two(self):
        asset = {
            'readme_raw': base64.b64encode(self.bc.fake.text().encode('utf-8')).decode('utf-8'),
            'readme_url': self.bc.fake.url(),
        }
        model = self.bc.database.create(asset=asset)
        url = reverse_lazy('registry:asset_slug_extension',
                           kwargs={
                               'asset_slug': model.asset.slug,
                               'extension': 'md'
                           })
        response = self.client.get(url)
        text = response.content.decode('utf-8')
        expected = '\n'.join([
            f'# {model.asset.title}', '',
            f'Readme file in language `None` was not found for this {model.asset.asset_type.lower()}.', '',
            'This error was reported to our team and it will be fixed soon. In the mean time, try looking for the lesson in a different language.'
        ])
        self.assertEqual(text, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [self.bc.format.to_dict(model.asset)])

    @patch('frontmatter.loads', MagicMock(side_effect=Exception('They killed kenny')))
    def test_number_three(self):
        asset = {
            'readme_raw': base64.b64encode(self.bc.fake.text().encode('utf-8')).decode('utf-8'),
            'readme_url': self.bc.fake.url(),
        }
        model = self.bc.database.create(asset=asset)
        url = reverse_lazy('registry:asset_slug_extension',
                           kwargs={
                               'asset_slug': model.asset.slug,
                               'extension': 'md'
                           })
        response = self.client.get(url)
        text = response.content.decode('utf-8')
        expected = '\n'.join([
            f'# {model.asset.title}', '',
            f'Readme file in language `None` was not found for this {model.asset.asset_type.lower()}.', '',
            'This error was reported to our team and it will be fixed soon. In the mean time, try looking for the lesson in a different language.',
            ''
        ])
        self.assertEqual(text, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [self.bc.format.to_dict(model.asset)])

    @patch('frontmatter.loads', MagicMock(MagicMock(return_value={'random': 'dictionary'})))
    def test_number_four(self):
        decoded = base64.b64encode(self.bc.fake.text().encode('utf-8')).decode('utf-8')
        asset = {
            'readme_raw': decoded,
            'readme_url': self.bc.fake.url(),
        }
        model = self.bc.database.create(asset=asset)
        url = reverse_lazy('registry:asset_slug_extension',
                           kwargs={
                               'asset_slug': model.asset.slug,
                               'extension': 'md'
                           })
        response = self.client.get(url)
        text = response.content.decode('utf-8')
        expected = '\n'.join([
            f'# {model.asset.title}', '',
            f'Readme file in language `None` was not found for this {model.asset.asset_type.lower()}.', '',
            'This error was reported to our team and it will be fixed soon. In the mean time, try looking for the lesson in a different language.',
            ''
        ])
        self.assertEqual(text, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [self.bc.format.to_dict(model.asset)])
