from datetime import datetime, timedelta, timezone

import capyc.pytest as capy
import pytest
from django.contrib.auth import get_user_model
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework.test import APIClient

from breathecode.admissions.models import City, Country
from breathecode.authenticate.models import Token
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
                "name": keyword_cluster.academy.name,
            }
        ),
        "keywords": [],
        "lang": keyword_cluster.lang,
        "landing_page_url": keyword_cluster.landing_page_url,
        "total_articles": 0,
    }


@pytest.mark.parametrize("lang", ["us", "es"])
def test_get_keyword_cluster_us(client: capy.Client, database: capy.Database, fake: capy.Fake, bc, lang):
    url = reverse_lazy("registry:academy_keywordcluster")

    model = database.create(
        keyword_cluster=[
            {
                "slug": "web",
                "title": "web",
                "lang": lang,
                "visibility": "PUBLIC",
                "landing_page_url": None,
                "is_deprecated": False,
                "is_important": True,
                "is_urgent": True,
                "internal_description": None,
                "optimization_rating": None,
            }
        ],
        user={
            "username": fake.slug(),
            "email": fake.email(),
        },
        academy=1,
        role=1,
        profile_academy=1,
        city=1,
        country=1,
        capability={"slug": "read_keywordcluster"},
    )

    client.force_authenticate(user=model.user)

    response = client.get(f"{url}?lang={lang}", headers={"academy": 1})
    json = response.json()

    expected = [serialize_keyword_cluster(model.keyword_cluster)]

    assert expected == json
    assert response.status_code == 200


@pytest.mark.parametrize("lang, query_lang", [["es", "us"], ["us", "es"]])
def test_get_keyword_cluster_no_match(
    client: capy.Client,
    database: capy.Database,
    fake: capy.Fake,
    bc,
    lang,
    query_lang,
):
    url = reverse_lazy("registry:academy_keywordcluster")

    model = database.create(
        keyword_cluster=[
            {
                "slug": "web",
                "title": "web",
                "lang": lang,
                "visibility": "PUBLIC",
                "landing_page_url": None,
                "is_deprecated": False,
                "is_important": True,
                "is_urgent": True,
                "internal_description": None,
                "optimization_rating": None,
            }
        ],
        user={
            "username": fake.slug(),
            "email": fake.email(),
        },
        academy=1,
        role=1,
        profile_academy=1,
        city=1,
        country=1,
        capability={"slug": "read_keywordcluster"},
    )

    client.force_authenticate(user=model.user)

    response = client.get(f"{url}?lang={query_lang}", headers={"academy": 1})
    json = response.json()

    expected = []

    assert json == expected
    assert response.status_code == 200


# def test_get_keyword_cluster_non_us(client: capy.Client, database: capy.Database, fake: capy.Fake, bc):
#     url = reverse_lazy("registry:academy_keywordcluster")

#     model = database.create(
#         keyword_cluster=[
#             {
#                 "slug": "web",
#                 "title": "web",
#                 "lang": "es",
#                 "visibility": "PUBLIC",
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             }
#         ],
#         user={
#             "username": fake.slug(),
#             "email": fake.email(),
#         },
#         role=1,
#         profile_academy=1,
#         city=1,
#         country=1,
#         capability={"slug": "read_keywordcluster"},
#     )

#     client.force_authenticate(user=model.user)

#     response = client.get(f"{url}?lang=es", headers={"academy": 1})
#     json = response.json()

#     expected = [serialize_keyword_cluster(model.keyword_cluster)]

#     assert expected == json
#     assert response.status_code == 200
