import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.talent_development.models import CareerPath, CareerStage, JobFamily, JobRole, Skill, SkillDomain, StageSkill


def create_academy():
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", defaults={"country": country})
    return Academy.objects.create(
        slug="downtown-miami-filtering",
        name="Downtown Miami Filtering",
        logo_url="https://assets.test/logo.png",
        street_address="123 Main Street",
        country=country,
        city=city,
    )


def grant_capability(user, academy, capability_slug="read_career_path"):
    capability, _ = Capability.objects.get_or_create(slug=capability_slug, defaults={"description": capability_slug})
    role, _ = Role.objects.get_or_create(slug=f"talent-{capability_slug}", defaults={"name": f"Talent {capability_slug}"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    return user


def make_framework(academy, *, role_slug="backend-dev", path_name="Backend Track"):
    job_family = JobFamily.objects.create(name="Engineering", slug=f"engineering-{role_slug}", academy=academy)
    job_role = JobRole.objects.create(
        name="Backend Developer",
        slug=role_slug,
        job_family=job_family,
        academy=academy,
    )
    career_path = CareerPath.objects.create(name=path_name, job_role=job_role, academy=academy)
    stage1 = CareerStage.objects.create(career_path=career_path, sequence=1, title="Junior", goal="", description="")
    stage2 = CareerStage.objects.create(career_path=career_path, sequence=2, title="Mid", goal="", description="")
    domain = SkillDomain.objects.create(name="Programming", slug=f"programming-{role_slug}", description="")
    return {
        "job_family": job_family,
        "job_role": job_role,
        "career_path": career_path,
        "stage1": stage1,
        "stage2": stage2,
        "domain": domain,
    }


@pytest.mark.django_db
def test_skills_can_filter_by_stage_ids_via_stage_skill(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u-s1", "u-s1@example.com", "pass1234"), academy, "read_career_path")
    tf = make_framework(academy, role_slug="backend-dev-s1", path_name="Backend Track S1")

    skill = Skill.objects.create(name="Docker", slug="docker-s1", domain=tf["domain"])
    StageSkill.objects.create(stage=tf["stage1"], skill=skill, required_level="core", is_core=True)

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_skill")
    r = client.get(url + f"?stage_ids={tf['stage1'].id}", HTTP_Academy=str(academy.id))

    assert r.status_code == status.HTTP_200_OK
    assert any(x["slug"] == "docker-s1" for x in r.data)


@pytest.mark.django_db
def test_skills_can_filter_by_career_path_ids_via_stage_skill(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u-s2", "u-s2@example.com", "pass1234"), academy, "read_career_path")
    tf = make_framework(academy, role_slug="backend-dev-s2", path_name="Backend Track S2")

    skill = Skill.objects.create(name="Kubernetes", slug="k8s-s2", domain=tf["domain"])
    StageSkill.objects.create(stage=tf["stage2"], skill=skill, required_level="applied", is_core=True)

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_skill")
    r = client.get(url + f"?career_path_ids={tf['career_path'].id}", HTTP_Academy=str(academy.id))

    assert r.status_code == status.HTTP_200_OK
    assert any(x["slug"] == "k8s-s2" for x in r.data)


@pytest.mark.django_db
def test_skills_can_filter_by_career_paths_name_via_stage_skill(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u-s3", "u-s3@example.com", "pass1234"), academy, "read_career_path")
    tf = make_framework(academy, role_slug="backend-dev-s3", path_name="Backend Track S3")

    skill = Skill.objects.create(name="Linux", slug="linux-s3", domain=tf["domain"])
    StageSkill.objects.create(stage=tf["stage1"], skill=skill, required_level="foundation", is_core=True)

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_skill")
    r = client.get(url + "?career_paths=Backend%20Track%20S3", HTTP_Academy=str(academy.id))

    assert r.status_code == status.HTTP_200_OK
    assert any(x["slug"] == "linux-s3" for x in r.data)


@pytest.mark.django_db
def test_career_paths_can_filter_by_job_role_slug_and_id(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u-cp", "u-cp@example.com", "pass1234"), academy, "read_career_path")

    tf1 = make_framework(academy, role_slug="role-a", path_name="Track A")
    tf2 = make_framework(academy, role_slug="role-b", path_name="Track B")

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_career_path")

    r_slug = client.get(url + "?job_roles=role-a", HTTP_Academy=str(academy.id))
    assert r_slug.status_code == status.HTTP_200_OK
    assert any(x["id"] == tf1["career_path"].id for x in r_slug.data)
    assert not any(x["id"] == tf2["career_path"].id for x in r_slug.data)

    r_id = client.get(url + f"?job_role_ids={tf2['job_role'].id}", HTTP_Academy=str(academy.id))
    assert r_id.status_code == status.HTTP_200_OK
    assert any(x["id"] == tf2["career_path"].id for x in r_id.data)
    assert not any(x["id"] == tf1["career_path"].id for x in r_id.data)


@pytest.mark.django_db
def test_career_stages_list_endpoint_filters_by_job_role_and_career_path(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("u-cs", "u-cs@example.com", "pass1234"), academy, "read_career_path")

    tf1 = make_framework(academy, role_slug="role-stages-a", path_name="Stages Track A")
    tf2 = make_framework(academy, role_slug="role-stages-b", path_name="Stages Track B")

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_career_stage")

    r_role = client.get(url + "?job_roles=role-stages-a", HTTP_Academy=str(academy.id))
    assert r_role.status_code == status.HTTP_200_OK
    assert all(x["career_path"]["job_role"]["slug"] == "role-stages-a" for x in r_role.data)

    r_path = client.get(url + f"?career_path_ids={tf2['career_path'].id}", HTTP_Academy=str(academy.id))
    assert r_path.status_code == status.HTTP_200_OK
    assert all(x["career_path"]["id"] == tf2["career_path"].id for x in r_path.data)

