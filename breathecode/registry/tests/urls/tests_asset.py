import pytest
from django.urls.base import reverse_lazy
from breathecode.tests.mixins.legacy import LegacyAPITestCase
from django.utils import timezone
from breathecode.tests.mixins.breathecode_mixin import Breathecode

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures('db')


def get_serializer(asset, data={}):
    return {
        'id':
        asset.id,
        'slug':
        asset.slug,
        'title':
        asset.title,
        'asset_type':
        asset.asset_type,
        'category': {
            'id': asset.category.id,
            'slug': asset.category.slug,
            'title': asset.category.title,
        },
        'description':
        asset.description,
        'difficulty':
        asset.difficulty,
        'duration':
        None,
        'external':
        False,
        'gitpod':
        False,
        'graded':
        False,
        'intro_video_url':
        None,
        'lang':
        asset.lang,
        'preview':
        None,
        'published_at':
        None,
        'readme_url':
        None,
        'solution_video_url':
        None,
        'status':
        'NOT_STARTED',
        'url':
        None,
        'translations': {},
        'technologies': [tech.slug for tech in asset.technologies.all()] if asset.technologies else [],
        'seo_keywords':
        [seo_keyword.slug for seo_keyword in asset.seo_keywords.all()] if asset.seo_keywords else [],
        'visibility':
        asset.visibility,
        **data,
    }


def get_serializer_technology(technology, data={}):
    return {
        'slug': technology.slug,
        'title': technology.title,
        'description': technology.description,
        'icon_url': technology.icon_url,
        'is_deprecated': technology.is_deprecated,
        **data,
    }


class TestRegistryAsset(LegacyAPITestCase):

    def test_with_no_assets(self, bc: Breathecode):

        Asset = bc.database.get_model('registry.Asset')

        url = reverse_lazy('registry:assets')
        response = self.client.get(url)
        json = response.json()

        assert bc.database.list_of('registry.Asset') == []
        assert json == []

    def test_one_asset(self, bc: Breathecode):

        model = bc.database.create(asset=1)

        url = reverse_lazy('registry:assets')
        response = self.client.get(url)
        json = response.json()

        expected = [get_serializer(model.asset)]

        assert json == expected
        assert bc.database.list_of('registry.Asset') == [bc.format.to_dict(model.asset)]

    def test_many_assets(self, bc: Breathecode):

        model = bc.database.create(asset=3)

        url = reverse_lazy('registry:assets')
        response = self.client.get(url)
        json = response.json()

        expected = [get_serializer(asset) for asset in model.asset]

        assert json == expected
        assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)

    def test_assets_technologies_expand(self, bc: Breathecode):

        technology = {'slug': 'learn-react', 'title': 'Learn React'}
        model = bc.database.create(asset_technology=(1, technology), asset=(3, {'technologies': 1}))

        url = reverse_lazy('registry:assets') + f'?expand=technologies'
        response = self.client.get(url)
        json = response.json()

        expected = [
            get_serializer(asset, data={'technologies': [get_serializer_technology(model.asset_technology)]})
            for asset in model.asset
        ]

        assert json == expected
        assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)
