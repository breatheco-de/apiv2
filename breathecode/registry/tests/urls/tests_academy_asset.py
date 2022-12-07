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
from breathecode.registry import tasks


def database_list_of_serializer(academy, category, data={}):
    return {
        'academy_id': academy.id,
        'assessment_id': academy.id,
        'asset_type': 'PROJECT',
        'author_id': None,
        'authors_username': None,
        'category_id': category.id,
        'cleaning_status': 'PENDING',
        'cleaning_status_details': None,
        'config': None,
        'delivery_formats': 'url',
        'delivery_instructions': None,
        'delivery_regex_url': None,
        'description': None,
        'difficulty': None,
        'duration': None,
        'external': False,
        'gitpod': False,
        'graded': False,
        'html': None,
        'interactive': False,
        'intro_video_url': None,
        'is_seo_tracked': True,
        'lang': None,
        'last_cleaning_at': None,
        'last_seo_scan_at': None,
        'last_synch_at': None,
        'last_test_at': None,
        'optimization_rating': None,
        'owner_id': None,
        'preview': None,
        'published_at': None,
        'readme': None,
        'readme_raw': None,
        'readme_url': None,
        'requirements': None,
        'seo_json_status': None,
        'slug': '',
        'solution_url': None,
        'solution_video_url': None,
        'status': 'UNASSIGNED',
        'status_text': None,
        'sync_status': None,
        'test_status': None,
        'title': '',
        'url': None,
        'visibility': 'PUBLIC',
        'with_solutions': False,
        'with_video': False,
        **data,
    }


def post_serializer(academy, category, data={}):

    return {
        'academy': {
            'id': academy.id,
            'name': academy.name
        },
        'asset_type': 'PROJECT',
        'author': None,
        'category': {
            'id': category.id,
            'slug': category.slug
        },
        'delivery_formats': 'url',
        'delivery_instructions': None,
        'delivery_regex_url': None,
        'description': None,
        'difficulty': None,
        'duration': None,
        'external': False,
        'gitpod': False,
        'graded': False,
        'id': academy.id,
        'interactive': False,
        'intro_video_url': None,
        'lang': None,
        'last_synch_at': None,
        'last_test_at': None,
        'owner': None,
        'preview': None,
        'published_at': None,
        'readme_url': None,
        'seo_keywords': [],
        'slug': '',
        'solution_url': None,
        'solution_video_url': None,
        'status': 'UNASSIGNED',
        'status_text': None,
        'sync_status': None,
        'technologies': [],
        'test_status': None,
        'title': 'model_title',
        'translations': {
            'null': 'model_slug'
        },
        'url': None,
        'visibility': 'PUBLIC',
        'with_solutions': False,
        'with_video': False,
        **data,
    }


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

    @patch('breathecode.registry.tasks.async_pull_from_github.delay', MagicMock())
    def test__post__with__all__mandatory__properties(self):
        """Test /Asset creation with all mandatory properties"""
        model = self.bc.database.create(
            role=1,
            capability='crud_asset',
            profile_academy=1,
            academy=1,
            user=1,
            asset_category=1,
        )

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy('registry:academy_asset')
        data = {'slug': 'model_slug', 'asset_type': 'PROJECT', 'category': 1, 'title': 'model_slug'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        del data['category']
        expected = post_serializer(model.academy, model.asset_category, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        #self.assertEqual(task.async_pull_from_github.call_args_list, [])
        #self.assertEqual(self.bc.database.list_of('registry.Asset'),
        #                 database_list_of_serializer(model.academy, model.asset_category))

    # def test__list__of__registry__asset__category(self):
    #     model = self.bc.database.create(
    #         role=1,
    #         capability='crud_asset',
    #         profile_academy=1,
    #         academy=1,
    #         user=1,
    #         asset_category=1,
    #     )

    #     self.bc.request.authenticate(model.user)
    #     self.bc.request.set_headers(academy=1)

    #     url = reverse_lazy('registry:academy_asset')
    #     data = {'slug': 'model_slug', 'asset_type': 'PROJECT', 'category': 1, 'title': 'model_slug'}
    #     response = self.client.post(url, data, format='json')
    #     json = response.json()
    #     del data['category']
    #     expected = database_list_of_serializer(model.academy, model.asset_category, data=data)

    #     self.assertEqual(self.bc.database.list_of('registry.Asset'), expected)
