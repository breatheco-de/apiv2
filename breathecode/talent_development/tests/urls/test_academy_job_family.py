import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.talent_development.models import JobFamily, JobRole


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


@pytest.mark.django_db
def test_create_job_family(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)

    url = reverse("talent_development:academy_job_family")
    payload = {"name": "Engineering", "description": "Handles engineering efforts"}

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_201_CREATED
    job_family = JobFamily.objects.get()
    assert job_family.name == "Engineering"
    assert job_family.slug == "engineering"
    assert job_family.academy == academy


@pytest.mark.django_db
def test_update_job_family(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)

    url = reverse("talent_development:academy_job_family_id", kwargs={"job_family_id": job_family.id})
    payload = {"description": "Updated description", "is_active": False}

    client.force_authenticate(user=user)
    response = client.put(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_200_OK
    job_family.refresh_from_db()
    assert job_family.description == "Updated description"
    assert job_family.is_active is False


@pytest.mark.django_db
def test_delete_job_family(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)

    url = reverse("talent_development:academy_job_family_id", kwargs={"job_family_id": job_family.id})

    client.force_authenticate(user=user)
    response = client.delete(url, HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert JobFamily.objects.count() == 0


@pytest.mark.django_db
def test_create_job_role(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)

    url = reverse("talent_development:academy_job_role")
    payload = {"name": "Backend Developer", "description": "Builds APIs", "job_family": job_family.id}

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_201_CREATED
    job_role = JobRole.objects.get()
    assert job_role.name == "Backend Developer"
    assert job_role.slug == "backend-developer"
    assert job_role.academy == academy
    assert job_role.job_family == job_family


@pytest.mark.django_db
def test_update_job_role(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)
    job_role = JobRole.objects.create(
        name="Backend Developer",
        slug="backend-developer",
        job_family=job_family,
        academy=academy,
        description="Builds APIs",
    )

    url = reverse("talent_development:academy_job_role_id", kwargs={"job_role_id": job_role.id})
    payload = {"description": "Owns backend stack", "is_active": False}

    client.force_authenticate(user=user)
    response = client.put(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_200_OK
    job_role.refresh_from_db()
    assert job_role.description == "Owns backend stack"
    assert job_role.is_active is False


@pytest.mark.django_db
def test_delete_job_role(client):
    academy = create_academy()
    user = grant_capability(User.objects.create_user("talent-user", "talent@example.com", "pass1234"), academy)
    job_family = JobFamily.objects.create(name="Engineering", slug="engineering", academy=academy)
    job_role = JobRole.objects.create(
        name="Backend Developer",
        slug="backend-developer",
        job_family=job_family,
        academy=academy,
        description="Builds APIs",
    )

    url = reverse("talent_development:academy_job_role_id", kwargs={"job_role_id": job_role.id})

    client.force_authenticate(user=user)
    response = client.delete(url, HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert JobRole.objects.count() == 0


