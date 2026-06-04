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
    StageCompetency,
    StageSkill,
)


def create_academy():
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", defaults={"country": country})
    return Academy.objects.create(
        slug="downtown-miami-fw",
        name="Downtown Miami FW",
        logo_url="https://assets.test/logo.png",
        street_address="123 Main Street",
        country=country,
        city=city,
    )


def grant_capability(user, academy, capability_slug="crud_career_path"):
    capability, _ = Capability.objects.get_or_create(slug=capability_slug, defaults={"description": capability_slug})
    role, _ = Role.objects.get_or_create(slug="talent-manager-fw", defaults={"name": "Talent Manager FW"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    return user


@pytest.mark.django_db
def test_create_and_delete_career_path(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u1", "u1@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Eng", slug="eng-fw", academy=academy)
    job_role = JobRole.objects.create(
        name="Dev",
        slug="dev-fw",
        job_family=job_family,
        academy=academy,
    )

    client.force_authenticate(user=user)
    create_url = reverse("talent_development:academy_career_path")
    r = client.post(
        create_url,
        {"name": "Track A", "job_role": job_role.id},
        format="json",
        HTTP_Academy=str(academy.id),
    )
    assert r.status_code == status.HTTP_201_CREATED
    path_id = r.data["id"]

    del_url = reverse("talent_development:academy_career_path_id", kwargs={"career_path_id": path_id})
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_204_NO_CONTENT
    assert CareerPath.objects.count() == 0


@pytest.mark.django_db
def test_delete_career_path_blocked_when_stages_exist(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u2", "u2@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Eng", slug="eng-fw2", academy=academy)
    job_role = JobRole.objects.create(
        name="Dev",
        slug="dev-fw2",
        job_family=job_family,
        academy=academy,
    )
    path = CareerPath.objects.create(name="Track", job_role=job_role, academy=academy)
    CareerStage.objects.create(career_path=path, sequence=1, title="S1", goal="", description="")

    client.force_authenticate(user=user)
    del_url = reverse("talent_development:academy_career_path_id", kwargs={"career_path_id": path.id})
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_and_delete_career_stage(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u3", "u3@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Eng", slug="eng-fw3", academy=academy)
    job_role = JobRole.objects.create(
        name="Dev",
        slug="dev-fw3",
        job_family=job_family,
        academy=academy,
    )
    path = CareerPath.objects.create(name="Track", job_role=job_role, academy=academy)

    client.force_authenticate(user=user)
    post_url = reverse("talent_development:academy_career_path_id_career_stage", kwargs={"career_path_id": path.id})
    r = client.post(
        post_url,
        {"sequence": 1, "title": "Junior", "goal": "Learn", "description": ""},
        format="json",
        HTTP_Academy=str(academy.id),
    )
    assert r.status_code == status.HTTP_201_CREATED
    stage_id = r.data["id"]

    del_url = reverse(
        "talent_development:academy_career_path_id_career_stage_id",
        kwargs={"career_path_id": path.id, "career_stage_id": stage_id},
    )
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_delete_career_stage_blocked_with_stage_skill(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u4", "u4@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Eng", slug="eng-fw4", academy=academy)
    job_role = JobRole.objects.create(
        name="Dev",
        slug="dev-fw4",
        job_family=job_family,
        academy=academy,
    )
    path = CareerPath.objects.create(name="Track", job_role=job_role, academy=academy)
    stage = CareerStage.objects.create(career_path=path, sequence=1, title="J", goal="", description="")
    domain = SkillDomain.objects.create(name="D", slug="d-fw4", description="")
    skill = Skill.objects.create(name="S", slug="s-fw4", domain=domain)
    StageSkill.objects.create(stage=stage, skill=skill)

    client.force_authenticate(user=user)
    del_url = reverse(
        "talent_development:academy_career_path_id_career_stage_id",
        kwargs={"career_path_id": path.id, "career_stage_id": stage.id},
    )
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_career_stage_blocked_with_stage_competency(client):
    from breathecode.talent_development.models import Competency

    academy = create_academy()
    user = grant_capability(User.objects.create_user("u5", "u5@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Eng", slug="eng-fw5", academy=academy)
    job_role = JobRole.objects.create(
        name="Dev",
        slug="dev-fw5",
        job_family=job_family,
        academy=academy,
    )
    path = CareerPath.objects.create(name="Track", job_role=job_role, academy=academy)
    stage = CareerStage.objects.create(career_path=path, sequence=1, title="J", goal="", description="")
    comp = Competency.objects.create(name="C", slug="c-fw5", type="technical")
    StageCompetency.objects.create(stage=stage, competency=comp)

    client.force_authenticate(user=user)
    del_url = reverse(
        "talent_development:academy_career_path_id_career_stage_id",
        kwargs={"career_path_id": path.id, "career_stage_id": stage.id},
    )
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_and_delete_skill_domain(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u6", "u6@example.com", "pass1234"), academy)

    client.force_authenticate(user=user)
    post_url = reverse("talent_development:academy_skill_domain")
    r = client.post(
        post_url,
        {"name": "Data Science", "description": "DS skills"},
        format="json",
        HTTP_Academy=str(academy.id),
    )
    assert r.status_code == status.HTTP_201_CREATED
    assert r.data["slug"] == "data-science"
    domain_id = r.data["id"]

    del_url = reverse("talent_development:academy_skill_domain_id", kwargs={"skill_domain_id": domain_id})
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_delete_skill_domain_blocked_when_skills_exist(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u7", "u7@example.com", "pass1234"), academy)
    domain = SkillDomain.objects.create(name="Dom", slug="dom-fw7", description="")
    Skill.objects.create(name="Sk", slug="sk-fw7", domain=domain)

    client.force_authenticate(user=user)
    del_url = reverse("talent_development:academy_skill_domain_slug", kwargs={"skill_domain_slug": "dom-fw7"})
    r_del = client.delete(del_url, HTTP_Academy=str(academy.id))
    assert r_del.status_code == status.HTTP_403_FORBIDDEN
