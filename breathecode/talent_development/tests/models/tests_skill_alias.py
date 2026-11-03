import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.registry.models import Asset, AssetSkill
from breathecode.talent_development.models import Skill, SkillAlias, SkillDomain


@pytest.fixture
def domain(db):
    return SkillDomain.objects.create(name="Programming", slug="programming", description="")


def create_skill(domain, slug="python-loops", name="Python loops"):
    return Skill.objects.create(slug=slug, name=name, domain=domain)


def test_rename_creates_alias(domain):
    skill = create_skill(domain)

    skill.slug = "python-iteration"
    skill.save()

    assert list(SkillAlias.objects.values_list("slug", "skill_id")) == [("python-loops", skill.id)]


def test_save_without_slug_change_does_not_create_alias(domain):
    skill = create_skill(domain)

    skill.name = "Loops in Python"
    skill.save()

    assert SkillAlias.objects.count() == 0


def test_rename_back_removes_alias_of_new_slug(domain):
    skill = create_skill(domain)

    skill.slug = "python-iteration"
    skill.save()
    skill.slug = "python-loops"
    skill.save()

    assert list(SkillAlias.objects.values_list("slug", flat=True)) == ["python-iteration"]


def test_rename_with_deferred_slug_does_not_crash(domain):
    create_skill(domain)

    skill = Skill.objects.only("id", "name").get()
    skill.name = "Renamed"
    skill.save()

    assert SkillAlias.objects.count() == 0


def test_get_by_slug_or_alias(domain):
    skill = create_skill(domain)
    skill.slug = "python-iteration"
    skill.save()

    assert Skill.get_by_slug_or_alias("python-iteration") == skill
    assert Skill.get_by_slug_or_alias("python-loops") == skill
    assert Skill.get_by_slug_or_alias("unknown") is None


def test_skill_clean_rejects_slug_used_by_alias_of_another_skill(domain):
    first = create_skill(domain)
    first.slug = "python-iteration"
    first.save()

    second = Skill(slug="python-loops", name="Other", domain=domain)
    with pytest.raises(ValidationError):
        second.clean()


def test_alias_clean_rejects_slug_used_by_skill(domain):
    skill = create_skill(domain)

    with pytest.raises(ValidationError):
        SkillAlias(slug="python-loops", skill=skill).clean()


def test_skill_used_by_asset_cannot_be_deleted(domain):
    skill = create_skill(domain)
    asset = Asset.objects.create(slug="intro-loops", title="Intro loops", asset_type="LESSON", lang="en")
    AssetSkill.objects.create(asset=asset, skill=skill)

    with pytest.raises(ProtectedError):
        skill.delete()


def create_academy():
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


def authenticate(client, academy):
    user = User.objects.create_user("talent-user", "talent@example.com", "pass1234")
    capability, _ = Capability.objects.get_or_create(
        slug="read_career_path", defaults={"description": "read_career_path"}
    )
    role, _ = Role.objects.get_or_create(slug="talent-reader", defaults={"name": "Talent Reader"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    client.force_authenticate(user=user)


def test_skill_by_slug_view_resolves_alias(client, domain):
    academy = create_academy()
    authenticate(client, academy)

    skill = create_skill(domain)
    skill.slug = "python-iteration"
    skill.save()

    url = reverse("talent_development:academy_skill_slug", kwargs={"skill_slug": "python-loops"})
    response = client.get(url, HTTP_ACADEMY=str(academy.id))

    assert response.status_code == 200
    assert response.json()["slug"] == "python-iteration"


def test_skill_by_slug_view_not_found(client, domain):
    academy = create_academy()
    authenticate(client, academy)

    url = reverse("talent_development:academy_skill_slug", kwargs={"skill_slug": "unknown"})
    response = client.get(url, HTTP_ACADEMY=str(academy.id))

    assert response.status_code == 404
