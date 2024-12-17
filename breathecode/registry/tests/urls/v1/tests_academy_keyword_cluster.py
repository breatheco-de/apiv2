from datetime import datetime, timedelta, timezone

import capyc.pytest as capy
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.admissions.models import City, Country
from breathecode.registry.models import Academy, KeywordCluster


def serialize_keyword_cluster(keyword_cluster):
    return {
        "id": keyword_cluster.id,
        "slug": keyword_cluster.slug,
        "title": keyword_cluster.title,
        "academy": (
            None
            if not keyword_cluster.academy
            else {
                "id": keyword_cluster.academy.id,
                "slug": keyword_cluster.academy.slug,
                "name": keyword_cluster.academy.name,
                "city": ({"name": keyword_cluster.academy.city.name} if keyword_cluster.academy.city else None),
                "country": (
                    {"name": keyword_cluster.academy.country.name} if keyword_cluster.academy.country else None
                ),
            }
        ),
        "lang": keyword_cluster.lang,
        "visibility": keyword_cluster.visibility,
        "landing_page_url": keyword_cluster.landing_page_url,
        "is_deprecated": keyword_cluster.is_deprecated,
        "is_important": keyword_cluster.is_important,
        "is_urgent": keyword_cluster.is_urgent,
        "internal_description": keyword_cluster.internal_description,
        "optimization_rating": keyword_cluster.optimization_rating,
        "created_at": keyword_cluster.created_at.isoformat(),
        "updated_at": keyword_cluster.updated_at.isoformat(),
    }


def test_get_keyword_cluster(client: capy.Client, database: capy.Database, fake: capy.Fake):
    # url = reverse_lazy("academy_keywordcluster")
    url = "academy/keywordcluster"

    # country = database.create(code=1, name=fake.country())

    model = database.create(
        city=1,
        country=1,
        academy={
            "slug": fake.slug(),
            "name": fake.name(),
            "logo_url": "https://example.com/logo.jpg",
            "street_address": "Address",
        },
        keyword_cluster=[
            {
                "slug": "web",
                "title": "web",
                "lang": "us",
                "visibility": "PUBLIC",
                "landing_page_url": None,
                "is_deprecated": False,
                "is_important": True,
                "is_urgent": True,
                "internal_description": None,
                "optimization_rating": None,
            }
        ],
    )

    print("keyword_cluster", model.keyword_cluster)

    expected = [serialize_keyword_cluster(model.keyword_cluster)]

    response = client.get(f"{url}?visibility=PUBLIC")
    json_response = response.json()

    assert response.status_code == 200
    assert json_response == expected


# def test_get_keyword_cluster(client: capy.Client, database: capy.Database, fake: capy.Fake):
#     url = reverse_lazy("academy_keywordcluster")

#     country = database.create({"model": Country, "fields": {"code": fake.country_code(), "name": fake.country()}})

#     city, created = City.objects.get_or_create(name=fake.city())

#     academy = database.create(
#         {
#             "model": Academy,
#             "fields": {
#                 "slug": fake.slug(),
#                 "name": fake.name(),
#                 "logo_url": "https://example.com/logo.jpg",
#                 "street_address": "Address",
#                 "city": city,
#                 "country": country,
#             },
#         }
#     )

#     keyword_cluster = database.create(
#         {
#             "model": KeywordCluster,
#             "fields": [
#                 {
#                     "slug": "web",
#                     "title": "web",
#                     "lang": "us",
#                     "academy": academy,
#                     "visibility": "PUBLIC",
#                     "landing_page_url": None,
#                     "is_deprecated": False,
#                     "is_important": True,
#                     "is_urgent": True,
#                     "internal_description": None,
#                     "optimization_rating": None,
#                 }
#             ],
#         }
#     )

#     response = client.get(f"{url}?visibility=PUBLIC")
#     json_response = response.json()

#     expected = [serialize_keyword_cluster(keyword_cluster[0])]

#     assert response.status_code == 200
#     assert json_response == expected


# def test_get_keyword_cluster(client: capy.Client, database: capy.Database, fake: capy.Fake):
#     url = reverse_lazy("academy_keywordcluster")

#     academy = database.create(
#         city=1,
#         country=1,
#         academy={
#             "slug": fake.slug(),
#             "name": fake.name(),
#             "logo_url": "https://example.com/logo.jpg",
#             "street_address": "Address",
#         },
#     )

#     keyword_cluster = database.create(
#         keyword_cluster=[
#             {
#                 "slug": "web",
#                 "title": "web",
#                 "lang": "us",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             }
#         ],
#     )
#     response = client.get(f"{url}?visibility=PUBLIC")
#     json_response = response.json()

#     expected = [serialize_keyword_cluster(keyword_cluster[0])]

#     assert response.status_code == 200
#     assert json_response == expected


# def test_get_keyword_cluster(client: capy.Client, database: capy.Database, fake: capy.Fake):
#     # Create mock data
#     url = reverse_lazy("academy_keywordcluster")
#     # Ensure that city and country objects exist before creating the academy
#     # city = database.create({"name": fake.city()})
#     # country = database.create({"name": fake.country()})

#     model = database.create(
#         city=1,
#         country=1,
#         academy={
#             "slug": fake.slug(),
#             "name": fake.name(),
#             "logo_url": "https://example.com/logo.jpg",
#             "street_address": "Address",
#         },
#         keyword_cluster=[
#             {
#                 "slug": "web",
#                 "title": "web",
#                 # "academy": academy.id,
#                 "lang": "us",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             }
#         ],
#     )

#     # Perform GET request with query parameters
#     # url = reverse_lazy("keywordcluster-list", kwargs={"academy_id": academy.id})

#     # Filtering by visibility as an example
#     response = client.get(f"{url}?visibility=PUBLIC")
#     json_response = response.json()

#     # Serialize the expected result
#     expected = [serialize_keyword_cluster(keyword_cluster[0])]

#     # Test that the status code is 200 and the response matches expected output
#     assert response.status_code == 200
#     assert json_response == expected


# def test_get_keyword_cluster_filter_by_lang(client: capy.Client, database: capy.Database, fake: capy.Fake):
#     # Create mock data for multiple keyword clusters
#     academy = database.create(
#         academy={
#             "slug": fake.slug(),
#             "name": fake.name(),
#             "logo_url": "https://example.com/logo.jpg",
#             "street_address": "Address",
#             "city": fake.city(),
#             "country": fake.country(),
#         }
#     )

#     keyword_clusters = database.create(
#         keywordcluster=[
#             {
#                 "slug": "web",
#                 "title": "web",
#                 "academy": academy.academy.id,
#                 "lang": "us",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             },
#             {
#                 "slug": "marketing",
#                 "title": "marketing",
#                 "academy": academy.academy.id,
#                 "lang": "es",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             },
#         ]
#     )

#     # Perform GET request with query parameter 'lang'
#     url = reverse_lazy("keywordcluster-list", kwargs={"academy_id": academy.academy.id})
#     response = client.get(f"{url}?lang=us")
#     json_response = response.json()

#     # Serialize the expected result (only the 'us' lang cluster)
#     expected = [serialize_keyword_cluster(keyword_clusters[0])]

#     # Test that the status code is 200 and the response matches expected output
#     assert response.status_code == 200
#     assert json_response == expected


# def test_get_keyword_cluster_with_search(client: capy.Client, database: capy.Database, fake: capy.Fake):
#     # Create mock data for a keyword cluster with searchable fields
#     academy = database.create(
#         academy={
#             "slug": fake.slug(),
#             "name": fake.name(),
#             "logo_url": "https://example.com/logo.jpg",
#             "street_address": "Address",
#         }
#     )

#     keyword_cluster = database.create(
#         keywordcluster=[
#             {
#                 "slug": "web",
#                 "title": "web development",
#                 "academy": academy.academy.id,
#                 "lang": "us",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             }
#         ]
#     )

#     # Perform GET request with search query 'web'
#     url = reverse_lazy("keywordcluster-list", kwargs={"academy_id": academy.academy.id})
#     response = client.get(f"{url}?like=web")
#     json_response = response.json()

#     # Serialize the expected result
#     expected = [serialize_keyword_cluster(keyword_cluster[0])]

#     # Test that the status code is 200 and the response matches expected output
#     assert response.status_code == 200
#     assert json_response == expected
