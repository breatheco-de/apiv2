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


def test_with_no_assets(bc: Breathecode, client):

    url = reverse_lazy('registry:asset')
    response = client.get(url)
    json = response.json()

    assert json == []
    assert bc.database.list_of('registry.Asset') == []


def test_one_asset(bc: Breathecode, client):

    model = bc.database.create(asset=1)

    url = reverse_lazy('registry:asset')
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset)]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == [bc.format.to_dict(model.asset)]


def test_many_assets(bc: Breathecode, client):

    model = bc.database.create(asset=3)

    url = reverse_lazy('registry:asset')
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(asset) for asset in model.asset]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_technologies_expand(bc: Breathecode, client):

    technology = {'slug': 'learn-react', 'title': 'Learn React'}
    model = bc.database.create(asset_technology=(1, technology), asset=(3, {'technologies': 1}))

    url = reverse_lazy('registry:asset') + f'?expand=technologies'
    response = client.get(url)
    json = response.json()

    expected = [
        get_serializer(asset, data={'technologies': [get_serializer_technology(model.asset_technology)]})
        for asset in model.asset
    ]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_slug(bc: Breathecode, client):

    assets = [{'slug': 'randy'}, {'slug': 'jackson'}]
    model = bc.database.create(asset=assets)

    url = reverse_lazy('registry:asset') + '?slug=randy'
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_lang(bc: Breathecode, client):

    assets = [{'lang': 'us'}, {'lang': 'es'}]
    model = bc.database.create(asset=assets)

    url = reverse_lazy('registry:asset') + '?language=en'
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_visibility(bc: Breathecode, client):

    assets = [{'visibility': 'PUBLIC'}, {'visibility': 'PRIVATE'}]
    model = bc.database.create(asset=assets)

    url = reverse_lazy('registry:asset') + '?visibility=PRIVATE'
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[1])]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_bad_academy(bc: Breathecode, client):

    model = bc.database.create(asset=2)

    url = reverse_lazy('registry:asset') + '?academy=banana'
    response = client.get(url)
    json = response.json()

    expected = {'detail': 'academy-id-must-be-integer', 'status_code': 400}

    assert json == expected
    assert response.status_code == 400
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_academy(bc: Breathecode, client):

    academies = bc.database.create(academy=2)
    assets = [{'academy': academies.academy[0]}, {'academy': academies.academy[1]}]
    model = bc.database.create(asset=assets)

    url = reverse_lazy('registry:asset') + '?academy=2'
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[1])]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)


def test_assets_with_category(bc: Breathecode, client):

    categories = [{'slug': 'how-to'}, {'slug': 'como'}]
    model_categories = bc.database.create(asset_category=categories)
    assets = [{
        'category': model_categories.asset_category[0]
    }, {
        'category': model_categories.asset_category[1]
    }]
    model = bc.database.create(asset=assets)

    url = reverse_lazy('registry:asset') + '?category=how-to'
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of('registry.Asset') == bc.format.to_dict(model.asset)
