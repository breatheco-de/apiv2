import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Academy, City, Country, Syllabus
from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from breathecode.marketing.models import COURSE_STATUS, Course, CourseTranslation


def _create_user_with_capability(academy, capability_slug="crud_course"):
    username = f"tester-{academy.slug}"
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="pass1234")
    capability, _ = Capability.objects.get_or_create(
        slug=capability_slug,
        defaults={"description": capability_slug},
    )
    role, _ = Role.objects.get_or_create(slug="marketing-manager", defaults={"name": "Marketing Manager"})
    role.capabilities.add(capability)
    ProfileAcademy.objects.create(user=user, academy=academy, role=role)
    return user


def _create_academy(slug="downtown-miami", name="Downtown Miami"):
    country, _ = Country.objects.get_or_create(code="US", defaults={"name": "United States"})
    city, _ = City.objects.get_or_create(name="Miami", country=country)

    return Academy.objects.create(
        slug=slug,
        name=name,
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

    url = reverse("marketing:academy_course_id", kwargs={"course_identifier": course.id})
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
        kwargs={"course_identifier": course.id},
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

    url = reverse("marketing:academy_course_id_translation", kwargs={"course_identifier": course.id})

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

    url = reverse("marketing:academy_course_id_course_modules", kwargs={"course_identifier": course.id})
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


@pytest.mark.django_db
def test_create_course_from_scratch(client):
    academy = _create_academy()
    user = _create_user_with_capability(academy)
    url = reverse("marketing:academy_course")

    payload = {
        "slug": "ai-engineering",
        "icon_url": "https://assets.test/ai-icon.png",
        "technologies": "python,llm",
        "visibility": "PUBLIC",
    }

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_201_CREATED
    assert Course.objects.filter(slug="ai-engineering", academy=academy).exists()


@pytest.mark.django_db
def test_clone_course_success_with_permissions(client):
    source_academy = _create_academy(slug="source-academy", name="Source Academy")
    destination_academy = _create_academy(slug="destination-academy", name="Destination Academy")
    user = _create_user_with_capability(source_academy)
    role = ProfileAcademy.objects.filter(user=user, academy=source_academy).first().role
    ProfileAcademy.objects.create(user=user, academy=destination_academy, role=role)

    syllabus = Syllabus.objects.create(slug="fs-base", name="Full Stack Base")
    source_course = Course.objects.create(
        slug="full-stack-source",
        academy=source_academy,
        is_listed=False,
        plan_slug="pro-plan",
        status="ARCHIVED",
        icon_url="https://assets.test/source-icon.png",
        technologies="python,react",
        visibility="UNLISTED",
        has_waiting_list=True,
        color="#123456",
        banner_image="https://assets.test/source-banner.png",
    )
    source_course.syllabus.add(syllabus)
    CourseTranslation.objects.create(
        course=source_course,
        lang="en",
        title="Source title",
        description="Source description",
        short_description="Short",
    )

    url = reverse("marketing:academy_course")
    payload = {
        "slug": "full-stack-clone",
        "source_course": source_course.slug,
    }

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(destination_academy.id))

    assert response.status_code == status.HTTP_201_CREATED
    clone = Course.objects.get(slug="full-stack-clone")
    assert clone.academy_id == destination_academy.id
    assert clone.visibility == source_course.visibility
    assert clone.icon_url == source_course.icon_url
    assert clone.syllabus.count() == 1
    assert clone.syllabus.first().id == syllabus.id
    assert CourseTranslation.objects.filter(course=clone, lang="en", title="Source title").exists()


@pytest.mark.django_db
def test_clone_course_rejects_without_source_permission(client):
    source_academy = _create_academy(slug="source-only", name="Source Only")
    destination_academy = _create_academy(slug="destination-only", name="Destination Only")
    source_course = Course.objects.create(
        slug="hidden-source-course",
        academy=source_academy,
        icon_url="https://assets.test/source-icon.png",
        technologies="python",
    )
    user = _create_user_with_capability(destination_academy)
    url = reverse("marketing:academy_course")

    payload = {
        "slug": "clone-attempt",
        "source_course": source_course.slug,
    }

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(destination_academy.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "source-course-forbidden"


@pytest.mark.django_db
def test_clone_course_slug_conflict(client):
    source_academy = _create_academy(slug="academy-1", name="Academy 1")
    destination_academy = _create_academy(slug="academy-2", name="Academy 2")
    source_course = Course.objects.create(
        slug="source-course",
        academy=source_academy,
        icon_url="https://assets.test/source-icon.png",
        technologies="python",
    )

    user = _create_user_with_capability(source_academy)
    role = ProfileAcademy.objects.filter(user=user, academy=source_academy).first().role
    ProfileAcademy.objects.create(user=user, academy=destination_academy, role=role)

    Course.objects.create(
        slug="taken-slug",
        academy=destination_academy,
        icon_url="https://assets.test/taken-icon.png",
        technologies="react",
    )

    url = reverse("marketing:academy_course")
    payload = {"slug": "taken-slug", "source_course": source_course.slug}

    client.force_authenticate(user=user)
    response = client.post(url, payload, format="json", HTTP_Academy=str(destination_academy.id))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "slug" in response.json()


def _course_list_payload(response):
    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    raise AssertionError(repr(data))


@pytest.mark.django_db
def test_list_academy_courses_multi_academy(client):
    academy_a = _create_academy(slug="list-a", name="List A")
    academy_b = _create_academy(slug="list-b", name="List B")
    user = _create_user_with_capability(academy_a)
    role = ProfileAcademy.objects.filter(user=user, academy=academy_a).first().role
    ProfileAcademy.objects.create(user=user, academy=academy_b, role=role)

    Course.objects.create(
        slug="course-only-a",
        academy=academy_a,
        icon_url="https://assets.test/a.png",
        technologies="python",
        visibility="PUBLIC",
    )
    Course.objects.create(
        slug="course-only-b",
        academy=academy_b,
        icon_url="https://assets.test/b.png",
        technologies="react",
        visibility="PUBLIC",
    )

    url = reverse("marketing:academy_course")
    client.force_authenticate(user=user)
    response = client.get(url, HTTP_Academy=f"{academy_a.id},{academy_b.id}")

    assert response.status_code == status.HTTP_200_OK
    slugs = {row["slug"] for row in _course_list_payload(response)}
    assert slugs == {"course-only-a", "course-only-b"}
    body = response.json()
    if isinstance(body, dict):
        assert "academy_scope" not in body


@pytest.mark.django_db
def test_list_academy_courses_read_aggregate_partial(client):
    academy_a = _create_academy(slug="partial-a", name="Partial A")
    academy_b = _create_academy(slug="partial-b", name="Partial B")
    user = _create_user_with_capability(academy_a)

    Course.objects.create(
        slug="partial-course-a",
        academy=academy_a,
        icon_url="https://assets.test/pa.png",
        technologies="python",
        visibility="PUBLIC",
    )
    Course.objects.create(
        slug="partial-course-b",
        academy=academy_b,
        icon_url="https://assets.test/pb.png",
        technologies="react",
        visibility="PUBLIC",
    )

    url = reverse("marketing:academy_course")
    client.force_authenticate(user=user)
    response = client.get(url, HTTP_Academy=f"{academy_a.id},{academy_b.id}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert isinstance(body, dict)
    assert "academy_scope" in body
    assert body["academy_scope"]["resolution"] == "partial"
    assert set(body["academy_scope"]["requested_academy_ids"]) == {academy_a.id, academy_b.id}
    assert body["academy_scope"]["applied_academy_ids"] == [academy_a.id]
    slugs = {row["slug"] for row in body["results"]}
    assert slugs == {"partial-course-a"}


@pytest.mark.django_db
def test_list_academy_courses_forbidden_no_matching_academy(client):
    academy_a = _create_academy(slug="forbid-a", name="Forbid A")
    academy_other = _create_academy(slug="forbid-other", name="Forbid Other")
    user = _create_user_with_capability(academy_a)

    url = reverse("marketing:academy_course")
    client.force_authenticate(user=user)
    response = client.get(url, HTTP_Academy=str(academy_other.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_academy_courses_includes_private_excludes_deleted(client):
    academy = _create_academy(slug="vis-academy", name="Vis Academy")
    user = _create_user_with_capability(academy)

    Course.objects.create(
        slug="staff-private-course",
        academy=academy,
        icon_url="https://assets.test/priv.png",
        technologies="python",
        visibility="PRIVATE",
    )
    deleted = Course.objects.create(
        slug="staff-deleted-course",
        academy=academy,
        icon_url="https://assets.test/del.png",
        technologies="python",
        visibility="PUBLIC",
    )
    Course.objects.filter(pk=deleted.pk).update(status="DELETED")

    url = reverse("marketing:academy_course")
    client.force_authenticate(user=user)
    response = client.get(url, HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_200_OK
    slugs = {row["slug"] for row in _course_list_payload(response)}
    assert "staff-private-course" in slugs
    assert "staff-deleted-course" not in slugs


@pytest.mark.django_db
def test_get_academy_course_by_identifier_returns_405(client):
    academy = _create_academy(slug="method-academy", name="Method Academy")
    user = _create_user_with_capability(academy)
    course = Course.objects.create(
        slug="method-course",
        academy=academy,
        icon_url="https://assets.test/m.png",
        technologies="python",
        visibility="PUBLIC",
    )

    url = reverse("marketing:academy_course_id", kwargs={"course_identifier": course.slug})
    client.force_authenticate(user=user)
    response = client.get(url, HTTP_Academy=str(academy.id))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

