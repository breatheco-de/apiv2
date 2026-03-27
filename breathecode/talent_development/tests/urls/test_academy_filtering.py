import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.talent_development.models import (
    CareerPath,
    CareerStage,
    Competency,
    CompetencySkill,
    JobFamily,
    JobRole,
    Skill,
    SkillAttitudeTag,
    SkillDomain,
    SkillKnowledgeItem,
    StageCompetency,
    StageSkill,
)


def create_academy(slug="downtown-miami-filtering", name="Downtown Miami Filtering"):
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", defaults={"country": country})
    return Academy.objects.create(
        slug=slug,
        name=name,
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


@pytest.mark.django_db
def test_career_stages_include_shared_and_exclude_other_academy(client):
    academy_a = create_academy(slug="academy-a-stages", name="Academy A Stages")
    academy_b = create_academy(slug="academy-b-stages", name="Academy B Stages")
    user = grant_capability(User.objects.create_user("u-cs-shared", "u-cs-shared@example.com", "pass1234"), academy_a)

    tf_a = make_framework(academy_a, role_slug="role-own-stages", path_name="Own Stages")
    tf_b = make_framework(academy_b, role_slug="role-other-stages", path_name="Other Stages")

    shared_family = JobFamily.objects.create(name="Shared Family Stages", slug="shared-family-stages", academy=None)
    shared_role = JobRole.objects.create(
        name="Shared Role Stages",
        slug="shared-role-stages",
        job_family=shared_family,
        academy=None,
    )
    shared_path = CareerPath.objects.create(name="Shared Path Stages", job_role=shared_role, academy=None)
    shared_stage = CareerStage.objects.create(career_path=shared_path, sequence=1, title="Shared", goal="", description="")

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_career_stage")
    r = client.get(url, HTTP_Academy=str(academy_a.id))

    assert r.status_code == status.HTTP_200_OK
    ids = {x["id"] for x in r.data}
    assert tf_a["stage1"].id in ids
    assert tf_a["stage2"].id in ids
    assert shared_stage.id in ids
    assert tf_b["stage1"].id not in ids
    assert tf_b["stage2"].id not in ids


@pytest.mark.django_db
def test_career_stages_academy_self_excludes_shared(client):
    academy = create_academy(slug="academy-self-stages", name="Academy Self Stages")
    user = grant_capability(User.objects.create_user("u-cs-self", "u-cs-self@example.com", "pass1234"), academy)
    tf = make_framework(academy, role_slug="role-self-stages", path_name="Self Stages")

    shared_family = JobFamily.objects.create(name="Shared Family Self", slug="shared-family-self-stages", academy=None)
    shared_role = JobRole.objects.create(
        name="Shared Role Self",
        slug="shared-role-self-stages",
        job_family=shared_family,
        academy=None,
    )
    shared_path = CareerPath.objects.create(name="Shared Path Self", job_role=shared_role, academy=None)
    shared_stage = CareerStage.objects.create(career_path=shared_path, sequence=1, title="Shared", goal="", description="")

    client.force_authenticate(user=user)
    url = reverse("talent_development:academy_career_stage")
    r = client.get(url + "?academy=self", HTTP_Academy=str(academy.id))

    assert r.status_code == status.HTTP_200_OK
    ids = {x["id"] for x in r.data}
    assert tf["stage1"].id in ids
    assert tf["stage2"].id in ids
    assert shared_stage.id not in ids


@pytest.mark.django_db
def test_skill_related_lists_respect_shared_and_cross_academy_visibility(client):
    academy_a = create_academy(slug="academy-a-skills", name="Academy A Skills")
    academy_b = create_academy(slug="academy-b-skills", name="Academy B Skills")
    user = grant_capability(User.objects.create_user("u-sk-vis", "u-sk-vis@example.com", "pass1234"), academy_a)

    tf_a = make_framework(academy_a, role_slug="role-own-skills", path_name="Own Skills")
    tf_b = make_framework(academy_b, role_slug="role-other-skills", path_name="Other Skills")

    shared_family = JobFamily.objects.create(name="Shared Family Skills", slug="shared-family-skills", academy=None)
    shared_role = JobRole.objects.create(
        name="Shared Role Skills",
        slug="shared-role-skills",
        job_family=shared_family,
        academy=None,
    )
    shared_path = CareerPath.objects.create(name="Shared Path Skills", job_role=shared_role, academy=None)
    shared_stage = CareerStage.objects.create(career_path=shared_path, sequence=1, title="Shared", goal="", description="")

    own_skill = Skill.objects.create(name="Own Skill", slug="own-skill-vis", domain=tf_a["domain"])
    other_skill = Skill.objects.create(name="Other Skill", slug="other-skill-vis", domain=tf_b["domain"])
    shared_domain = SkillDomain.objects.create(name="Shared Domain Skills", slug="shared-domain-skills", description="")
    shared_skill = Skill.objects.create(name="Shared Skill", slug="shared-skill-vis", domain=shared_domain)

    StageSkill.objects.create(stage=tf_a["stage1"], skill=own_skill, required_level="core", is_core=True)
    StageSkill.objects.create(stage=tf_b["stage1"], skill=other_skill, required_level="core", is_core=True)
    StageSkill.objects.create(stage=shared_stage, skill=shared_skill, required_level="core", is_core=True)

    competency = Competency.objects.create(name="Shared Competency Vis", slug="shared-competency-vis")
    StageCompetency.objects.create(stage=shared_stage, competency=competency, required_level="core", is_core=True)
    CompetencySkill.objects.create(competency=competency, skill=shared_skill, weight=100)

    SkillKnowledgeItem.objects.create(skill=shared_skill, description="Shared knowledge")
    SkillAttitudeTag.objects.create(skill=shared_skill, tag="shared attitude", description="shared")

    client.force_authenticate(user=user)

    skills_url = reverse("talent_development:academy_skill")
    skills_r = client.get(skills_url, HTTP_Academy=str(academy_a.id))
    assert skills_r.status_code == status.HTTP_200_OK
    skill_slugs = {x["slug"] for x in skills_r.data}
    assert "own-skill-vis" in skill_slugs
    assert "shared-skill-vis" in skill_slugs
    assert "other-skill-vis" not in skill_slugs

    competencies_url = reverse("talent_development:academy_competency")
    competencies_r = client.get(competencies_url, HTTP_Academy=str(academy_a.id))
    assert competencies_r.status_code == status.HTTP_200_OK
    assert any(x["slug"] == "shared-competency-vis" for x in competencies_r.data)

    domains_url = reverse("talent_development:academy_skill_domain")
    domains_r = client.get(domains_url, HTTP_Academy=str(academy_a.id))
    assert domains_r.status_code == status.HTTP_200_OK
    domain_slugs = {x["slug"] for x in domains_r.data}
    assert tf_a["domain"].slug in domain_slugs
    assert shared_domain.slug in domain_slugs
    assert tf_b["domain"].slug not in domain_slugs

    knowledge_url = reverse("talent_development:academy_skill_knowledge_item")
    knowledge_r = client.get(knowledge_url, HTTP_Academy=str(academy_a.id))
    assert knowledge_r.status_code == status.HTTP_200_OK
    assert any(x["skill"]["slug"] == "shared-skill-vis" for x in knowledge_r.data)

    attitude_url = reverse("talent_development:academy_skill_attitude_tag")
    attitude_r = client.get(attitude_url, HTTP_Academy=str(academy_a.id))
    assert attitude_r.status_code == status.HTTP_200_OK
    assert any(x["skill"]["slug"] == "shared-skill-vis" for x in attitude_r.data)

