"""
Test cases for /v1/auth/me/academy/<slug_or_id>/capabilities
"""

from django.urls import reverse_lazy
from rest_framework import status


def test_without_auth(client):
    """Test without authentication"""
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": "1"})
    response = client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_academy_not_found_by_id(client, database):
    """Test with non-existent academy by ID"""
    model = database.create(user=1)
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": "999"})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == 404
    # The response should have the slug field with the error
    assert "detail" in data or "slug" in data


def test_academy_not_found_by_slug(client, database):
    """Test with non-existent academy by slug"""
    model = database.create(user=1)
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": "non-existent"})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == 404
    # The response should have either detail or slug field with the error
    assert "detail" in data or "slug" in data


def test_no_profile_academies(client, database):
    """Test when user has no ProfileAcademy for the academy"""
    model = database.create(user=1, city=1, country=1, academy=1)
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": str(model.academy.id)})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_single_profile_academy_with_capabilities(client, database):
    """Test with one ProfileAcademy and capabilities"""
    from breathecode.authenticate.models import Role, Capability, ProfileAcademy
    from django.contrib.auth.models import User
    from breathecode.admissions.models import Academy
    
    database.create(capability={"slug": "read_student"})
    database.create(capability={"slug": "crud_student"})
    
    # Create role without capabilities first
    database.create(role={"slug": "admin", "name": "Admin"})
    # Get the actual model instance and add capabilities
    role_instance = Role.objects.get(slug="admin")
    capability1 = Capability.objects.get(slug="read_student")
    capability2 = Capability.objects.get(slug="crud_student")
    role_instance.capabilities.set([capability1, capability2])
    
    # First create user and academy
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
    )
    
    # Then create ProfileAcademy directly using Django ORM
    user = User.objects.get(id=model.user.id)
    academy = Academy.objects.get(id=model.academy.id)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role_instance, email=user.email)
    
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": str(model.academy.id)})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert "crud_student" in data
    assert "read_student" in data


def test_single_profile_academy_by_slug(client, database):
    """Test with academy slug instead of ID"""
    from breathecode.authenticate.models import Role, Capability, ProfileAcademy
    from django.contrib.auth.models import User
    from breathecode.admissions.models import Academy
    
    database.create(capability={"slug": "read_student"})
    database.create(capability={"slug": "crud_student"})
    
    # Create role without capabilities first
    database.create(role={"slug": "admin", "name": "Admin"})
    # Get the actual model instance and add capabilities
    role_instance = Role.objects.get(slug="admin")
    capability1 = Capability.objects.get(slug="read_student")
    capability2 = Capability.objects.get(slug="crud_student")
    role_instance.capabilities.set([capability1, capability2])
    
    # First create user and academy
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
    )
    
    # Then create ProfileAcademy directly using Django ORM
    user = User.objects.get(id=model.user.id)
    academy = Academy.objects.get(id=model.academy.id)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role_instance, email=user.email)
    
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": model.academy.slug})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert "crud_student" in data
    assert "read_student" in data


def test_multiple_profile_academies_with_duplicates(client, database):
    """Test with multiple ProfileAcademies having overlapping capabilities"""
    from breathecode.authenticate.models import Role, Capability, ProfileAcademy
    from django.contrib.auth.models import User
    from breathecode.admissions.models import Academy
    
    # Create capabilities
    database.create(capability={"slug": "read_student"})
    database.create(capability={"slug": "crud_student"})
    database.create(capability={"slug": "read_assignment"})
    
    # Create roles without capabilities first
    database.create(role={"slug": "teacher", "name": "Teacher"})
    role1_instance = Role.objects.get(slug="teacher")
    capability1 = Capability.objects.get(slug="read_student")
    capability2 = Capability.objects.get(slug="crud_student")
    role1_instance.capabilities.set([capability1, capability2])
    
    database.create(role={"slug": "assistant", "name": "Assistant"})
    role2_instance = Role.objects.get(slug="assistant")
    capability3 = Capability.objects.get(slug="read_assignment")
    role2_instance.capabilities.set([capability1, capability3])
    
    # Create user and academy
    model = database.create(user=1, city=1, country=1, academy=1)
    
    # Get the actual instances
    user_instance = User.objects.get(id=model.user.id)
    academy_instance = Academy.objects.get(id=model.academy.id)
    
    # Create multiple ProfileAcademies for the same user and academy with different roles
    ProfileAcademy.objects.create(user=user_instance, academy=academy_instance, role=role1_instance, email=user_instance.email)
    ProfileAcademy.objects.create(user=user_instance, academy=academy_instance, role=role2_instance, email=user_instance.email)
    
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": str(model.academy.id)})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    # Should have 3 unique capabilities: read_student, crud_student, read_assignment
    assert len(data) == 3
    assert "read_student" in data
    assert "crud_student" in data
    assert "read_assignment" in data
    # Verify no duplicates
    assert len(data) == len(set(data))


def test_profile_academy_in_different_academy(client, database):
    """Test that ProfileAcademy in different academy doesn't return capabilities"""
    from breathecode.authenticate.models import Role, Capability, ProfileAcademy
    from breathecode.admissions.models import Academy
    
    database.create(capability={"slug": "read_student"})
    
    # Create role without capabilities first
    database.create(role={"slug": "admin", "name": "Admin"})
    role_instance = Role.objects.get(slug="admin")
    capability1 = Capability.objects.get(slug="read_student")
    role_instance.capabilities.set([capability1])
    
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=2,  # Create 2 academies
    )
    
    # Get first academy and create ProfileAcademy there
    academy1 = Academy.objects.first()
    ProfileAcademy.objects.create(user=model.user, academy=academy1, role=role_instance, email=model.user.email)
    
    # Request capabilities for academy 2 (where user has no ProfileAcademy)
    academy2 = Academy.objects.exclude(id=academy1.id).first()
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": str(academy2.id)})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_sorted_capabilities(client, database):
    """Test that capabilities are returned sorted alphabetically"""
    from breathecode.authenticate.models import Role, Capability, ProfileAcademy
    from django.contrib.auth.models import User
    from breathecode.admissions.models import Academy
    
    database.create(capability={"slug": "zebra_capability"})
    database.create(capability={"slug": "alpha_capability"})
    database.create(capability={"slug": "beta_capability"})
    
    # Create role without capabilities first
    database.create(role={"slug": "admin", "name": "Admin"})
    role_instance = Role.objects.get(slug="admin")
    capability1 = Capability.objects.get(slug="zebra_capability")
    capability2 = Capability.objects.get(slug="alpha_capability")
    capability3 = Capability.objects.get(slug="beta_capability")
    role_instance.capabilities.set([capability1, capability2, capability3])
    
    # First create user and academy
    model = database.create(
        user=1,
        city=1,
        country=1,
        academy=1,
    )
    
    # Then create ProfileAcademy directly using Django ORM
    user = User.objects.get(id=model.user.id)
    academy = Academy.objects.get(id=model.academy.id)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role_instance, email=user.email)
    
    url = reverse_lazy("authenticate:me_academy_capabilities", kwargs={"slug_or_id": str(model.academy.id)})
    client.force_authenticate(user=model.user)
    
    response = client.get(url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == ["alpha_capability", "beta_capability", "zebra_capability"]
