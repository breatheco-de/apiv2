import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse

from breathecode.admissions.models import Academy, City, Country, Syllabus, SyllabusVersion
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.registry.actions import set_asset_skills
from breathecode.registry.models import Asset
from breathecode.talent_development.models import Skill, SkillDomain


@pytest.fixture(autouse=True)
def setup(db):
    cache.clear()
    domain = SkillDomain.objects.create(name="Programming", slug="programming", description="")
    Skill.objects.create(slug="python-loops", name="Python loops", domain=domain)
    asset = Asset.objects.create(slug="loops-lesson", title="Loops", asset_type="LESSON", lang="en")
    set_asset_skills(asset, ["python-loops"])
    yield
    cache.clear()


def create_academy(slug):
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", defaults={"country": country})
    return Academy.objects.create(
        slug=slug,
        name=slug,
        logo_url="https://assets.test/logo.png",
        street_address="123 Main Street",
        country=country,
        city=city,
    )


def authenticate(client, academy, capability_slug="read_syllabus"):
    user = User.objects.create_user("syllabus-user", "syllabus@example.com", "pass1234")
    capability, _ = Capability.objects.get_or_create(slug=capability_slug, defaults={"description": capability_slug})
    role, _ = Role.objects.get_or_create(slug="syllabus-reader", defaults={"name": "Syllabus Reader"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    client.force_authenticate(user=user)


def create_syllabus(academy, private=False, versions=((1, "PUBLISHED"),)):
    syllabus = Syllabus.objects.create(slug="full-stack", name="Full Stack", academy_owner=academy, private=private)
    for version, status in versions:
        SyllabusVersion.objects.create(
            syllabus=syllabus,
            version=version,
            status=status,
            json={"days": [{"position": 1, "lessons": [{"slug": "loops-lesson"}]}]},
        )
    return syllabus


def get(client, academy, syllabus_id, version, query=""):
    url = reverse(
        "admissions:syllabus_id_version_skills", kwargs={"syllabus_id": str(syllabus_id), "version": str(version)}
    )
    return client.get(url + query, HTTP_ACADEMY=str(academy.id))


def test_without_auth(client):
    academy = create_academy("downtown-miami")
    create_syllabus(academy)

    response = get(client, academy, "full-stack", 1)

    assert response.status_code == 401


def test_without_capability(client):
    academy = create_academy("downtown-miami")
    authenticate(client, academy, capability_slug="read_cohort")
    create_syllabus(academy)

    response = get(client, academy, "full-stack", 1)

    assert response.status_code == 403


@pytest.mark.parametrize("syllabus_ref", ["full-stack", "id"])
def test_by_slug_or_id(client, syllabus_ref):
    academy = create_academy("downtown-miami")
    authenticate(client, academy)
    syllabus = create_syllabus(academy)

    response = get(client, academy, syllabus.id if syllabus_ref == "id" else syllabus.slug, 1)
    json = response.json()

    assert response.status_code == 200
    assert json["syllabus"] == "full-stack"
    assert json["version"] == 1
    assert json["total_assets"] == 1
    assert [x["slug"] for x in json["skills"]] == ["python-loops"]


def test_latest_is_the_highest_published_version(client):
    academy = create_academy("downtown-miami")
    authenticate(client, academy)
    create_syllabus(academy, versions=((1, "PUBLISHED"), (2, "PUBLISHED"), (3, "DRAFT")))

    response = get(client, academy, "full-stack", "latest")

    assert response.status_code == 200
    assert response.json()["version"] == 2


def test_private_syllabus_of_another_academy(client):
    owner = create_academy("downtown-miami")
    other = create_academy("madrid")
    authenticate(client, other)
    create_syllabus(owner, private=True)

    response = get(client, other, "full-stack", 1)

    assert response.status_code == 404
    assert response.json()["detail"] == "syllabus-version-not-found"


def test_public_syllabus_of_another_academy(client):
    owner = create_academy("downtown-miami")
    other = create_academy("madrid")
    authenticate(client, other)
    create_syllabus(owner, private=False)

    response = get(client, other, "full-stack", 1)

    assert response.status_code == 200


def test_deleted_version_requires_status_param(client):
    academy = create_academy("downtown-miami")
    authenticate(client, academy)
    create_syllabus(academy, versions=((1, "DELETED"),))

    response = get(client, academy, "full-stack", 1)
    assert response.status_code == 404

    response = get(client, academy, "full-stack", 1, "?status=DELETED")
    assert response.status_code == 200


def test_invalid_version(client):
    academy = create_academy("downtown-miami")
    authenticate(client, academy)
    create_syllabus(academy)

    response = get(client, academy, "full-stack", "first")

    assert response.status_code == 404
