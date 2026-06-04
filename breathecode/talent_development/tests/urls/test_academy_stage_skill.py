import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.talent_development.models import (
    CareerPath,
    CareerStage,
    JobFamily,
    JobRole,
    Skill,
    SkillDomain,
    StageSkill,
)


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


def grant_capability(user, academy, capability_slug="crud_career_path"):
    capability, _ = Capability.objects.get_or_create(slug=capability_slug, defaults={"description": capability_slug})
    role, _ = Role.objects.get_or_create(slug="talent-manager", defaults={"name": "Talent Manager"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    return user


def talent_framework_for_academy(academy):
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)
    job_role = JobRole.objects.create(
        name="Backend Developer",
        slug="backend-developer",
        job_family=job_family,
        academy=academy,
    )
    career_path = CareerPath.objects.create(
        name="Default Track",
        job_role=job_role,
        academy=academy,
    )
    stage = CareerStage.objects.create(
        career_path=career_path,
        sequence=1,
        title="Junior",
        goal="",
        description="",
    )
    domain = SkillDomain.objects.create(name="Programming", slug="programming", description="")
    return {"job_family": job_family, "job_role": job_role, "career_path": career_path, "stage": stage, "domain": domain}


@pytest.mark.django_db
def test_post_stage_skill_creates_skill_and_stage_skill(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    tf = talent_framework_for_academy(academy)

    url = reverse("talent_development:academy_stage_skill")
    payload = {
        "stage_id": tf["stage"].id,
        "name": "GraphQL APIs",
        "domain_id": tf["domain"].id,
        "required_level": "core",
        "is_core": True,
    }

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["skill"]["slug"] == "graphql-apis"
    assert response.data["skill"]["name"] == "GraphQL APIs"
    assert response.data["stage_skill"]["required_level"] == "core"
    assert response.data["stage_skill"]["is_core"] is True

    skill = Skill.objects.get(slug="graphql-apis")
    assert skill.domain_id == tf["domain"].id
    assert StageSkill.objects.filter(stage=tf["stage"], skill=skill).exists()


@pytest.mark.django_db
def test_post_stage_skill_upsert_returns_200(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user2", "talent2@example.com", "pass1234"), academy)
    tf = talent_framework_for_academy(academy)

    url = reverse("talent_development:academy_stage_skill")
    payload = {
        "stage_id": tf["stage"].id,
        "name": "REST APIs",
        "domain_slug": "programming",
        "required_level": "foundation",
        "is_core": False,
    }

    client.force_authenticate(user=user)
    r1 = client.post(url, payload, format="json", HTTP_Academy=str(academy.id))
    assert r1.status_code == status.HTTP_201_CREATED

    payload2 = {
        **payload,
        "required_level": "applied",
        "is_core": True,
    }
    r2 = client.post(url, payload2, format="json", HTTP_Academy=str(academy.id))
    assert r2.status_code == status.HTTP_200_OK
    assert r2.data["stage_skill"]["required_level"] == "applied"
    assert r2.data["stage_skill"]["is_core"] is True
    assert StageSkill.objects.filter(stage=tf["stage"]).count() == 1
