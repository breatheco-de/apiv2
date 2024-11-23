"""
Test /answer
"""

import random
import string
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.registry.caches import TechnologyCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ...mixins import RegistryTestCase


def get_serializer(asset_technology, assets=[], asset_technologies=[], data={}):
    return {
        "alias": asset_technologies,
        "assets": assets,
        "lang": None,
        "description": asset_technology.description,
        "icon_url": asset_technology.icon_url,
        "is_deprecated": asset_technology.is_deprecated,
        "parent": (
            {
                "description": asset_technology.description,
                "icon_url": asset_technology.icon_url,
                "is_deprecated": asset_technology.is_deprecated,
                "slug": asset_technology.slug,
                "title": asset_technology.title,
                "visibility": asset_technology.visibility,
            }
            if asset_technology.parent
            else None
        ),
        "slug": asset_technology.slug,
        "title": asset_technology.title,
        "visibility": asset_technology.visibility,
        "sort_priority": asset_technology.sort_priority,
        "marketing_information": asset_technology.marketing_information,
        **data,
    }


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy("registry:academy_technology")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("registry.Asset"), [])

    def test_without_academy_id(self):
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("registry:academy_technology")
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test_without_capability(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
        )
        url = reverse_lazy("registry:academy_technology")
        response = self.client.get(url)
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_technology for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET with zero AssetTechnology
    """

    def test_with_zero_asset_technologies(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, role=1, capability="read_technology")
        url = reverse_lazy("registry:academy_technology")
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("registry.AssetTechnology"), [])

    """
    🔽🔽🔽 GET with two AssetTechnology
    """

    def test_with_two_asset_technologies(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset_technology=(
                2,
                {
                    "visibility": "PUBLIC",
                },
            ),
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology")
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(x) for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing include_children
    """

    def test_with_two_asset_technologies__passing_include_children_as_false(self):
        self.headers(academy=1)
        asset_technologies = [{"parent_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + "?include_children=false"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_include_children_as_true(self):
        self.headers(academy=1)
        asset_technologies = [{"visibility": "PUBLIC", "parent_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + "?include_children=true"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset.slug], asset_technologies=[x.slug])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing language
    """

    def test_with_two_asset_technologies__passing_language__not_found(self):
        query = random.choices(string.ascii_lowercase, k=2)
        random.shuffle(query)

        lang = random.choices(string.ascii_lowercase, k=2)
        random.shuffle(lang)

        while query == lang:
            lang = random.choices(string.ascii_lowercase, k=2)
            random.shuffle(lang)

        query = "".join(query)
        lang = "".join(lang)

        asset_technologies = [{"lang": lang} for _ in range(0, 2)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )

        self.headers(academy=model.academy.id)

        url = reverse_lazy("registry:academy_technology") + f"?language={query}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

        # teardown
        self.bc.database.delete("registry.AssetTechnology")

    def test_with_two_asset_technologies__passing_language__found(self):
        cases = [("en", "us"), ("us", "us"), ("es", "es"), ("es", ""), ("es", None)]
        for query, value in cases:
            asset_technologies = [{"visibility": "PUBLIC", "lang": value} for _ in range(0, 2)]
            model = self.generate_models(
                authenticate=True,
                profile_academy=True,
                role=1,
                asset_technology=asset_technologies,
                capability="read_technology",
            )

            self.headers(academy=model.academy.id)

            url = reverse_lazy("registry:academy_technology") + f"?language={query}"
            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(x, data={"lang": value})
                for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("registry.AssetTechnology"),
                self.bc.format.to_dict(model.asset_technology),
            )

            # teardown
            self.bc.database.delete("registry.AssetTechnology")

    """
    🔽🔽🔽 GET with two AssetTechnology, passing sort_priority
    """

    def test_with_two_asset_technologies__passing_sort_priority__not_found(self):
        cases = (
            40,
            50,
            60,
        )
        query = random.choice(cases)

        sort_priority = random.choice(cases)

        while query == sort_priority:
            sort_priority = random.choice(cases)

        asset_technologies = [
            {"sort_priority": sort_priority, "slug": self.bc.fake.slug(), "title": self.bc.fake.slug()}
            for _ in range(0, 2)
        ]

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )

        self.headers(academy=model.academy.id)

        url = reverse_lazy("registry:academy_technology") + f"?sort_priority={query}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

        # teardown
        self.bc.database.delete("registry.AssetTechnology")

    def test_with_two_asset_technologies__passing_sort_priority__found(self):
        cases = (
            1,
            2,
            3,
        )
        query = random.choice(cases)

        sort_priority = query

        asset_technologies = [
            {
                "visibility": "PUBLIC",
                "sort_priority": sort_priority,
                "slug": self.bc.fake.slug(),
                "title": self.bc.fake.slug(),
            }
            for _ in range(0, 2)
        ]

        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )

        self.headers(academy=model.academy.id)

        url = reverse_lazy("registry:academy_technology") + f"?sort_priority={query}"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(x) for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

        # teardown
        self.bc.database.delete("registry.AssetTechnology")

    """
    🔽🔽🔽 GET with two AssetTechnology, passing like
    """

    def test_with_two_asset_technologies__passing_like__not_found(self):
        slug = self.bc.fake.slug()

        model = self.generate_models(
            authenticate=True, profile_academy=True, role=1, asset_technology=2, capability="read_technology"
        )

        self.headers(academy=model.academy.id)

        url = reverse_lazy("registry:academy_technology") + f"?like={slug}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_like__found(self):
        title1 = self.bc.fake.name()
        title2 = self.bc.fake.name()
        slug1 = self.bc.fake.slug()
        slug2 = self.bc.fake.slug()

        cases = [
            ("slug", slug1[0 : random.randint(1, len(slug1))], slug1),
            ("slug", slug2[0 : random.randint(1, len(slug2))], slug2),
            ("title", title1[0 : random.randint(1, len(title1))], title1),
            ("title", title2[0 : random.randint(1, len(title2))], title2),
        ]
        for field, query, value in cases:
            asset_technologies = [{"visibility": "PUBLIC", field: f"{value}{n}"} for n in range(0, 2)]
            model = self.generate_models(
                authenticate=True,
                profile_academy=True,
                role=1,
                asset_technology=asset_technologies,
                capability="read_technology",
            )

            self.headers(academy=model.academy.id)

            url = reverse_lazy("registry:academy_technology") + f"?like={query}"
            response = self.client.get(url)
            json = response.json()
            expected = [get_serializer(x) for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("registry.AssetTechnology"),
                self.bc.format.to_dict(model.asset_technology),
            )

            # teardown
            self.bc.database.delete("registry.AssetTechnology")

    """
    🔽🔽🔽 GET with two AssetTechnology, passing parent
    """

    def test_with_two_asset_technologies__passing_parent__not_found(self):
        self.headers(academy=1)
        asset_technologies = [{"parent_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + "?parent=3,4"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_parent__found(self):
        self.headers(academy=1)
        asset_technologies = [{"visibility": "PUBLIC", "parent_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + "?parent=1,2"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset.slug], asset_technologies=[x.slug])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing visibility
    """

    def test_with_two_asset_technologies__passing_visibility__not_found(self):
        statuses = ["PUBLIC", "UNLISTED", "PRIVATE"]

        query1 = random.choice(statuses)

        statuses.pop(statuses.index(query1))

        query2 = random.choice(statuses)
        statuses.pop(statuses.index(query2))

        self.headers(academy=1)
        asset_technologies = [{"visibility": statuses[0]} for _ in range(0, 2)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?visibility={query1},{query2}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_visibility__found(self):
        statuses = ["PUBLIC", "UNLISTED", "PRIVATE"]

        query1 = random.choice(statuses)

        statuses.pop(statuses.index(query1))

        query2 = random.choice(statuses)
        statuses.pop(statuses.index(query2))

        self.headers(academy=1)
        asset_technologies = [{"visibility": s} for s in [query1, query2]]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?visibility={query1},{query2}"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset.slug], asset_technologies=[])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing slug
    """

    def test_with_two_asset_technologies__passing_slug__not_found(self):
        slug1 = self.bc.fake.slug()
        slug2 = self.bc.fake.slug()

        self.headers(academy=1)

        model = self.generate_models(
            authenticate=True, profile_academy=True, role=1, asset=1, asset_technology=2, capability="read_technology"
        )
        url = reverse_lazy("registry:academy_technology") + f"?slug={slug1},{slug2}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_slug__found(self):
        slug1 = self.bc.fake.slug()
        slug2 = self.bc.fake.slug()

        self.headers(academy=1)

        asset_technologies = [{"visibility": "PUBLIC", "slug": s} for s in [slug1, slug2]]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=1,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?slug={slug1},{slug2}"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset.slug], asset_technologies=[])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing asset_slug
    """

    def test_with_two_asset_technologies__passing_asset_slug__not_found(self):
        slug1 = self.bc.fake.slug()
        slug2 = self.bc.fake.slug()

        self.headers(academy=1)

        asset_technologies = [{"featured_asset_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=2,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?asset_slug={slug1},{slug2}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_asset_slug__found(self):
        slug1 = self.bc.fake.slug()
        slug2 = self.bc.fake.slug()

        self.headers(academy=1)

        assets = [{"slug": s} for s in [slug1, slug2]]
        asset_technologies = [{"visibility": "PUBLIC", "featured_asset_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=assets,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?asset_slug={slug1},{slug2}"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset[0].slug, model.asset[1].slug], asset_technologies=[])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET with two AssetTechnology, passing asset_type
    """

    def test_with_two_asset_technologies__passing_asset_type__not_found(self):
        statuses = ["PROJECT", "EXERCISE", "LESSON", "QUIZ", "VIDEO", "ARTICLE"]

        query1 = random.choice(statuses)

        statuses.pop(statuses.index(query1))

        query2 = random.choice(statuses)
        statuses.pop(statuses.index(query2))

        self.headers(academy=1)

        asset_technologies = [{"featured_asset_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=2,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?asset_slug={query1},{query2}"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    def test_with_two_asset_technologies__passing_asset_type__found(self):
        statuses = ["PROJECT", "EXERCISE", "LESSON", "QUIZ", "VIDEO", "ARTICLE"]

        query1 = random.choice(statuses)

        statuses.pop(statuses.index(query1))

        query2 = random.choice(statuses)
        statuses.pop(statuses.index(query2))

        self.headers(academy=1)

        assets = [{"asset_type": s} for s in [query1, query2]]
        asset_technologies = [{"visibility": "PUBLIC", "featured_asset_id": n} for n in range(1, 3)]
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            role=1,
            asset=assets,
            asset_technology=asset_technologies,
            capability="read_technology",
        )
        url = reverse_lazy("registry:academy_technology") + f"?asset_type={query1},{query2}"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(x, assets=[model.asset[0].slug, model.asset[1].slug], asset_technologies=[])
            for x in sorted(model.asset_technology, key=lambda x: x.slug, reverse=True)
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("registry.AssetTechnology"),
            self.bc.format.to_dict(model.asset_technology),
        )

    """
    🔽🔽🔽 GET spy extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_spy_extensions(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, role=1, asset_technology=2, capability="read_technology"
        )
        url = reverse_lazy("registry:academy_technology")
        self.client.get(url)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=TechnologyCache, sort="-slug", paginate=True),
            ],
        )
