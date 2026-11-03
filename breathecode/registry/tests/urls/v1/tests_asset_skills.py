import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.registry.actions import set_asset_skills
from breathecode.registry.models import Asset, AssetCategory, AssetSkill
from breathecode.talent_development.models import Skill, SkillDomain


@pytest.fixture(autouse=True)
def clear_skills_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def academy(db):
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", defaults={"country": country})
    return Academy.objects.create(
        slug="downtown-miami",
        name="Downtown Miami",
        logo_url="https://assets.test/logo.png",
        street_address="123 Main Street",
        country=country,
        city=city,
    )


@pytest.fixture
def assets(academy):
    domain = SkillDomain.objects.create(name="Programming", slug="programming", description="")
    for slug in ["python-loops", "http-basics"]:
        Skill.objects.create(slug=slug, name=slug, domain=domain)

    category = AssetCategory.objects.create(slug="python", title="Python", lang="us", academy=academy)
    loops = Asset.objects.create(
        slug="loops-lesson",
        title="Loops",
        asset_type="LESSON",
        lang="us",
        academy=academy,
        status="PUBLISHED",
        category=category,
    )
    http = Asset.objects.create(
        slug="http-lesson", title="HTTP", asset_type="LESSON", lang="us", academy=academy, status="PUBLISHED"
    )
    Asset.objects.create(
        slug="empty-lesson", title="Empty", asset_type="LESSON", lang="us", academy=academy, status="PUBLISHED"
    )

    set_asset_skills(loops, [{"slug": "python-loops", "level": "core"}])
    set_asset_skills(http, ["http-basics"])
    return {"loops": loops, "http": http}


def authenticate(client, academy):
    user = User.objects.create_user("content-user", "content@example.com", "pass1234")
    role, _ = Role.objects.get_or_create(slug="content-manager", defaults={"name": "Content Manager"})
    for slug in ["read_asset", "crud_asset"]:
        capability, _ = Capability.objects.get_or_create(slug=slug, defaults={"description": slug})
        role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    client.force_authenticate(user=user)


def results(response):
    json = response.json()
    return json["results"] if isinstance(json, dict) and "results" in json else json


def test_academy_asset_list_includes_skills(client, academy, assets):
    authenticate(client, academy)

    response = client.get(reverse("registry:academy_asset"), HTTP_ACADEMY=str(academy.id))
    items = {x["slug"]: x for x in results(response)}

    assert response.status_code == 200
    assert items["loops-lesson"]["skills"] == [
        {"slug": "python-loops", "name": "python-loops", "domain": "programming", "level": "core"}
    ]
    assert items["loops-lesson"]["skills_source"] == "FILE"
    assert items["empty-lesson"]["skills"] == []
    assert items["empty-lesson"]["skills_source"] is None


@pytest.mark.parametrize(
    "query, expected",
    [
        ("python-loops", ["loops-lesson"]),
        ("python-loops,http-basics", ["http-lesson", "loops-lesson"]),
        ("unknown", []),
    ],
)
def test_academy_asset_list_filter_by_skills(client, academy, assets, query, expected):
    authenticate(client, academy)

    response = client.get(reverse("registry:academy_asset") + f"?skills={query}", HTTP_ACADEMY=str(academy.id))

    assert response.status_code == 200
    assert sorted(x["slug"] for x in results(response)) == expected


def test_academy_asset_list_reflects_skill_changes(client, academy, assets):
    authenticate(client, academy)
    url = reverse("registry:academy_asset")

    client.get(url, HTTP_ACADEMY=str(academy.id))
    set_asset_skills(assets["http"], ["http-basics", "python-loops"])
    response = client.get(url + "?skills=python-loops", HTTP_ACADEMY=str(academy.id))

    assert sorted(x["slug"] for x in results(response)) == ["http-lesson", "loops-lesson"]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("python-loops", ["loops-lesson"]),
        ("python-loops,http-basics", ["http-lesson", "loops-lesson"]),
    ],
)
def test_public_asset_list_filter_by_skills(client, assets, query, expected):
    response = client.get(reverse("registry:asset") + f"?skills={query}")

    assert response.status_code == 200
    assert sorted(x["slug"] for x in results(response)) == expected


def test_put_ignores_skills(client, academy, assets):
    authenticate(client, academy)
    url = reverse("registry:academy_asset") + "/loops-lesson"

    response = client.put(
        url,
        {"skills": ["http-basics"], "skills_source": "INHERITED", "title": "Loops 2"},
        format="json",
        HTTP_ACADEMY=str(academy.id),
    )

    assert response.status_code == 200
    loops = Asset.objects.get(slug="loops-lesson")
    assert loops.title == "Loops 2"
    assert loops.skills_source == "FILE"
    assert list(AssetSkill.objects.filter(asset=loops).values_list("skill__slug", flat=True)) == ["python-loops"]
