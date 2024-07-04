from unittest.mock import MagicMock, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin import Breathecode
from breathecode.utils.api_view_extensions.extensions import lookup_extension

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


def get_serializer(asset, data={}):
    asset_translations = {}
    for translation in asset.all_translations.all():
        asset_translations[translation.lang or "null"] = translation.slug

    return {
        "id": asset.id,
        "slug": asset.slug,
        "title": asset.title,
        "asset_type": asset.asset_type,
        "category": {
            "id": asset.category.id,
            "slug": asset.category.slug,
            "title": asset.category.title,
        },
        "description": asset.description,
        "assets_related": (
            [
                {
                    "id": related.id,
                    "slug": related.slug,
                    "lang": related.lang,
                    "asset_type": related.asset_type,
                    "status": related.status,
                    "published_at": related.published_at,
                    "category": {
                        "id": related.category.id,
                        "slug": related.category.slug,
                        "title": related.category.title,
                    },
                    "technologies": (
                        [get_serializer_technology(tech) for tech in related.technologies.all()]
                        if related.technologies
                        else []
                    ),
                }
                for related in asset.assets_related.all()
            ]
            if asset.assets_related
            else []
        ),
        "difficulty": asset.difficulty,
        "duration": asset.duration,
        "external": asset.external,
        "gitpod": asset.gitpod,
        "graded": asset.graded,
        "intro_video_url": asset.intro_video_url,
        "lang": asset.lang,
        "preview": asset.preview,
        "published_at": asset.published_at,
        "readme_url": asset.readme_url,
        "solution_video_url": asset.solution_video_url,
        "solution_url": asset.solution_url,
        "status": asset.status,
        "url": asset.url,
        "translations": asset_translations,
        "technologies": [tech.slug for tech in asset.technologies.all()] if asset.technologies else [],
        "seo_keywords": [seo_keyword.slug for seo_keyword in asset.seo_keywords.all()] if asset.seo_keywords else [],
        "visibility": asset.visibility,
        **data,
    }


def get_serializer_technology(technology, data={}):
    return {
        "slug": technology.slug,
        "title": technology.title,
        "description": technology.description,
        "icon_url": technology.icon_url,
        "is_deprecated": technology.is_deprecated,
        "visibility": technology.visibility,
        **data,
    }


def test_with_no_assets(bc: Breathecode, client):

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    assert json == []
    assert bc.database.list_of("registry.Asset") == []


def test_one_asset(bc: Breathecode, client):

    model = bc.database.create(asset={"status": "PUBLISHED"})

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset)]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_many_assets(bc: Breathecode, client):

    model = bc.database.create(asset=(3, {"status": "PUBLISHED"}))

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(asset) for asset in model.asset]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_technologies_expand(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}
    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            3,
            {
                "technologies": 1,
                "status": "PUBLISHED",
            },
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=technologies"
    response = client.get(url)
    json = response.json()

    expected = [
        get_serializer(asset, data={"technologies": [get_serializer_technology(model.asset_technology)]})
        for asset in model.asset
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_slug(bc: Breathecode, client):

    assets = [
        {
            "slug": "randy",
            "status": "PUBLISHED",
        },
        {
            "slug": "jackson",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?slug=randy"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_lang(bc: Breathecode, client):

    assets = [
        {
            "lang": "us",
            "status": "PUBLISHED",
        },
        {
            "lang": "es",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?language=en"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets__hidden_all_non_visibilities(bc: Breathecode, client):

    assets = [
        {
            "visibility": "PUBLIC",
            "status": "PUBLISHED",
        },
        {
            "visibility": "PRIVATE",
            "status": "PUBLISHED",
        },
        {
            "visibility": "UNLISTED",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_bad_academy(bc: Breathecode, client):

    model = bc.database.create(asset=2)

    url = reverse_lazy("registry:asset") + "?academy=banana"
    response = client.get(url)
    json = response.json()

    expected = {"detail": "academy-id-must-be-integer", "status_code": 400}

    assert json == expected
    assert response.status_code == 400
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_academy(bc: Breathecode, client):

    academies = bc.database.create(academy=2)
    assets = [
        {
            "academy": academies.academy[0],
            "status": "PUBLISHED",
        },
        {
            "academy": academies.academy[1],
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?academy=2"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[1])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_category(bc: Breathecode, client):

    categories = [{"slug": "how-to"}, {"slug": "como"}]
    model_categories = bc.database.create(asset_category=categories)
    assets = [
        {
            "category": model_categories.asset_category[0],
            "status": "PUBLISHED",
        },
        {
            "category": model_categories.asset_category[1],
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?category=how-to"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


@patch(
    "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
    MagicMock(wraps=lookup_extension.compile_lookup),
)
def test_lookup_extension(bc: Breathecode, client):

    assets = [
        {
            "asset_type": "LESSON",
            "status": "PUBLISHED",
        },
        {
            "asset_type": "PROJECT",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    args, kwargs = bc.format.call(
        "en",
        strings={
            "iexact": [
                "test_status",
                "sync_status",
            ],
            "in": ["difficulty", "status", "asset_type", "category__slug", "technologies__slug", "seo_keywords__slug"],
        },
        ids=["author", "owner"],
        bools={
            "exact": ["with_video", "interactive", "graded"],
        },
        overwrite={
            "category": "category__slug",
            "technologies": "technologies__slug",
            "seo_keywords": "seo_keywords__slug",
        },
    )

    query = bc.format.lookup(*args, **kwargs)
    url = reverse_lazy("registry:asset") + "?" + bc.format.querystring(query)

    assert [x for x in query] == [
        "author",
        "owner",
        "test_status",
        "sync_status",
        "difficulty",
        "status",
        "asset_type",
        "category",
        "technologies",
        "seo_keywords",
        "with_video",
        "interactive",
        "graded",
    ]

    response = client.get(url)

    json = response.json()

    expected = []

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)
