"""
    🔽🔽🔽 Testing Asset Creation without category
"""

from unittest.mock import MagicMock, patch, call
from django.urls.base import reverse_lazy
from rest_framework import status
from django.test import TestCase
from breathecode.registry.models import Asset
from ..mixins import RegistryTestCase
from ...models import AssetCategory


class RegistryTestAsset(RegistryTestCase):

    def test__without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('registry:academy_asset')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

    def test__without_capability(self):
        """Test /certificate without auth"""
        self.headers(academy=1)
        url = reverse_lazy('registry:academy_asset')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'status_code': 403,
            'detail': "You (user: 1) don't have this capability: read_asset for academy 1"
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

    def test__post__without_category(self):
        """Test /Asset without category"""
        model = self.generate_models(role=1, capability='crud_asset', profile_academy=1, academy=1, user=1)

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('registry:academy_asset')
        data = {'slug': 'model_slug', 'asset_type': 'PROJECT'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'category': ['This field cannot be blank.'],
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])

    def test__post__with__all__mandatory__propertys(self):
        """Test /Asset creation with all mandatory propertys"""
        #id_category = AssetCategory.id
        model = self.bc.database.create(
            role=1,
            capability='crud_asset',
            profile_academy=1,
            academy=1,
            user=1,
        )

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy('registry:academy_asset')
        data = {'slug': 'model_slug', 'asset_type': 'PROJECT', 'category': id_category}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('registry.Asset'), [])
