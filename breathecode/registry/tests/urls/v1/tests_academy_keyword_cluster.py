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
def test_get_keyword_cluster_no_match_lang(
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


@pytest.mark.parametrize("lang", ["es", "us", " es", "es ", " us", "us ", " es ", " us ", "", " "])
def test_get_keyword_cluster_lang_strip(
    client: capy.Client,
    database: capy.Database,
    fake: capy.Fake,
    bc,
    lang,
):
    url = reverse_lazy("registry:academy_keywordcluster")

    clean_lang = lang.strip()

    if clean_lang in ["es", "us"]:
        model = database.create(
            keyword_cluster=[
                {
                    "slug": "web",
                    "title": "web",
                    "lang": lang.strip(),
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
        response = client.get(f"{url}?lang={clean_lang}", headers={"academy": 1})
        json = response.json()

        expected = [serialize_keyword_cluster(model.keyword_cluster)]

        assert json == expected
        assert response.status_code == 200


@pytest.mark.parametrize(
    "like, expected_slug",
    [
        ("web", "web"),
        ("we", "web"),
        ("", "web"),
        ("undefined", "web"),
    ],
)
def test_get_keyword_cluster_like(
    client: capy.Client, database: capy.Database, fake: capy.Fake, bc, like, expected_slug
):
    url = reverse_lazy("registry:academy_keywordcluster")

    model = database.create(
        keyword_cluster=[
            {
                "slug": "web",
                "title": "web for developers",
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

    response = client.get(f"{url}?like={like}", headers={"academy": 1})
    json = response.json()

    if expected_slug:
        assert json, f"Expected results for 'like={like}', but got an empty response"
        assert any(cluster["slug"] == expected_slug for cluster in json)
    else:
        assert json == []


@pytest.mark.parametrize(
    "visibility, expected_count, expected_status_code",
    [
        (None, 1, 200),  # Sin parámetro, se espera visibilidad pública por defecto
        ("PUBLIC", 1, 200),  # Con 'visibility=PUBLIC', se espera 1 resultado público
        ("PRIVATE", 1, 200),  # Con 'visibility=PRIVATE', se espera 1 resultado privado
        ("INVALID", 0, 400),  # Con 'visibility=INVALID', no debe devolver resultados
    ],
)
def test_get_keyword_cluster_visibility(
    client: capy.Client,
    database: capy.Database,
    fake: capy.Fake,
    bc,
    visibility,
    expected_count,
    expected_status_code,
):
    url = reverse_lazy("registry:academy_keywordcluster")

    # Crear los modelos con diferentes valores de 'visibility'
    model = database.create(
        keyword_cluster=[
            {
                "slug": "web",
                "title": "Web para desarrolladores",
                "lang": "us",
                "visibility": "PUBLIC",  # Público
                "landing_page_url": None,
                "is_deprecated": False,
                "is_important": True,
                "is_urgent": True,
                "internal_description": None,
                "optimization_rating": None,
            },
            {
                "slug": "seo",
                "title": "Consejos SEO",
                "lang": "us",
                "visibility": "PRIVATE",  # Privado
                "landing_page_url": None,
                "is_deprecated": False,
                "is_important": False,
                "is_urgent": True,
                "internal_description": None,
                "optimization_rating": None,
            },
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

    # Realizar la solicitud GET con el parámetro 'visibility'
    params = {"visibility": visibility} if visibility else {}
    response = client.get(f"{url}?academy_id=1", params=params, headers={"academy": 1})
    json = response.json()

    # Verificar la cantidad de elementos y el código de estado
    assert len(json) == expected_count
    assert response.status_code == expected_status_code

    # Verificar el mensaje de error para la prueba "INVALID" (opcional)
    if visibility == "INVALID" and expected_status_code == 400:
        assert "Valor de visibilidad no válido" in response.text


# def test_get_keyword_cluster_visibility_invalid(
#     client: capy.Client,
#     database: capy.Database,
#     fake: capy.Fake,
#     bc,
# ):
#     url = reverse_lazy("registry:academy_keywordcluster")

#     # Crear los modelos
#     model = database.create(
#         keyword_cluster=[
#             {
#                 "slug": "web",
#                 "title": "Web for developers",
#                 "lang": "us",
#                 "visibility": "PUBLIC",  # Público
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": True,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             },
#             {
#                 "slug": "seo",
#                 "title": "SEO Tips",
#                 "lang": "us",
#                 "visibility": "PRIVATE",  # Privado
#                 "landing_page_url": None,
#                 "is_deprecated": False,
#                 "is_important": False,
#                 "is_urgent": True,
#                 "internal_description": None,
#                 "optimization_rating": None,
#             },
#         ],
#         user={
#             "username": fake.slug(),
#             "email": fake.email(),
#         },
#         academy=1,
#         role=1,
#         profile_academy=1,
#         city=1,
#         country=1,
#         capability={"slug": "read_keywordcluster"},
#     )

#     client.force_authenticate(user=model.user)

#     # Realizar la solicitud GET con un valor de 'visibility' no válido
#     response = client.get(f"{url}?academy_id=1&visibility=INVALID", headers={"academy": 1})

#     # Verificar que el código de estado es 400 (Bad Request)
#     assert response.status_code == 400
#     assert "Invalid visibility value" in response.data  # Mensaje de error esperado
