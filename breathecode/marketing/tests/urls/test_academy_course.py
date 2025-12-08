import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.marketing.models import COURSE_STATUS, Course, CourseTranslation


def _create_user_with_capability(academy, capability_slug="crud_course"):
    user = User.objects.create_user(username="tester", email="tester@example.com", password="pass1234")
    capability, _ = Capability.objects.get_or_create(
        slug=capability_slug,
        defaults={"description": capability_slug},
    )
    role, _ = Role.objects.get_or_create(slug="marketing-manager", defaults={"name": "Marketing Manager"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    return user


def _create_academy():
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", country=country)

    return Academy.objects.create(
        slug="downtown-miami",
        name="Downtown Miami",
        logo_url="https://assets.test/logo.png",
        street_address="123 Main Street",
        country=country,
        city=city,
    )


@pytest.mark.django_db
def test_update_course(client):
    academy = _create_academy()
    course = Course.objects.create(
        slug="full-stack",
        academy=academy,
        is_listed=True,
        plan_slug="full-stack-us",
        status=COURSE_STATUS[0][0],
        icon_url="https://assets.test/course-icon.png",
        technologies="python,react",
        visibility="PUBLIC",
    )
    user = _create_user_with_capability(academy)

    url = reverse("marketing:academy_course_id", kwargs={"course_id": course.id})
    payload = {
        "plan_slug": "full-stack-global",
        "is_listed": False,
        "status": "ARCHIVED",
        "color": "#112233",
    }

    client.force_authenticate(user=user)
    response = client.put(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_200_OK
    course.refresh_from_db()
    assert course.plan_slug == "full-stack-global"
    assert course.is_listed is False
    assert course.status == "ARCHIVED"
    assert course.color == "#112233"


@pytest.mark.django_db
def test_update_plan_by_country_code(client):
    academy = _create_academy()
    course = Course.objects.create(
        slug="data-science",
        academy=academy,
        is_listed=True,
        plan_slug="data-science-us",
        status=COURSE_STATUS[0][0],
        icon_url="https://assets.test/course-icon.png",
        technologies="python,pandas",
        visibility="PUBLIC",
    )
    user = _create_user_with_capability(academy)

    url = reverse(
        "marketing:academy_course_id_plan_by_country_code",
        kwargs={"course_id": course.id},
    )
    payload = {"plan_by_country_code": {"us": "data-science-us", "co": "data-science-co"}}

    client.force_authenticate(user=user)
    response = client.put(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_200_OK
    course.refresh_from_db()
    assert course.plan_by_country_code == {"us": "data-science-us", "co": "data-science-co"}


@pytest.mark.django_db
def test_update_course_translation_requires_lang(client):
    academy = _create_academy()
    course = Course.objects.create(
        slug="ux-design",
        academy=academy,
        is_listed=True,
        plan_slug="ux-design-us",
        status=COURSE_STATUS[0][0],
        icon_url="https://assets.test/course-icon.png",
        technologies="figma,ux",
        visibility="PUBLIC",
    )
    CourseTranslation.objects.create(
        course=course,
        lang="en",
        title="UX Design",
        description="Learn UX Design",
        short_description="UX",
    )
    user = _create_user_with_capability(academy)

    url = reverse("marketing:academy_course_id_translation", kwargs={"course_id": course.id})

    client.force_authenticate(user=user)
    response = client.put(url, {"title": "New Title"}, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "missing-lang"


@pytest.mark.django_db
def test_update_course_modules(client):
    academy = _create_academy()
    course = Course.objects.create(
        slug="machine-learning",
        academy=academy,
        is_listed=True,
        plan_slug="ml-us",
        status=COURSE_STATUS[0][0],
        icon_url="https://assets.test/course-icon.png",
        technologies="python,scikit",
        visibility="PUBLIC",
    )
    translation = CourseTranslation.objects.create(
        course=course,
        lang="en",
        title="Machine Learning",
        description="ML Description",
        short_description="ML",
    )
    user = _create_user_with_capability(academy)

    url = reverse("marketing:academy_course_id_course_modules", kwargs={"course_id": course.id})
    new_modules = [
        {"name": "Foundations", "slug": "foundations", "description": "Math basics"},
        {"name": "Supervised", "slug": "supervised", "description": "Supervised learning"},
    ]

    client.force_authenticate(user=user)
    response = client.put(
        url,
        {"lang": translation.lang, "course_modules": new_modules},
        format="json",
        HTTP_Academy=str(academy.id),
    )

    assert response.status_code == status.HTTP_200_OK
    translation.refresh_from_db()
    assert translation.course_modules == new_modules

