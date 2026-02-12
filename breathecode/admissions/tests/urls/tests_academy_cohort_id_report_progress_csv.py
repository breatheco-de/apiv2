"""
Tests for /v1/admissions/academy/cohort/<id>/report.csv
"""

import csv
from io import StringIO

from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status


def _setup_reporting_role(database):
    from breathecode.authenticate.models import Capability, Role

    database.create(capability={"slug": "academy_reporting"})
    database.create(role={"slug": "reporting", "name": "Reporting"})

    role = Role.objects.get(slug="reporting")
    capability = Capability.objects.get(slug="academy_reporting")
    role.capabilities.set([capability])
    role.save()

    return role


def test_progress_report_is_filtered_by_cohort(database, client):
    from breathecode.admissions.models import Cohort, CohortUser
    from breathecode.authenticate.models import ProfileAcademy

    role = _setup_reporting_role(database)

    staff = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=staff.user, academy=staff.academy, role=role, email=staff.user.email)

    student_a = database.create(user=1).user
    student_b = database.create(user=1).user
    student_c = database.create(user=1).user

    cohort_1 = Cohort.objects.create(
        slug="cohort-progress-1",
        name="Cohort Progress 1",
        kickoff_date=timezone.now(),
        academy=staff.academy,
    )
    cohort_2 = Cohort.objects.create(
        slug="cohort-progress-2",
        name="Cohort Progress 2",
        kickoff_date=timezone.now(),
        academy=staff.academy,
    )

    CohortUser.objects.create(user=student_a, cohort=cohort_1, role="STUDENT")
    CohortUser.objects.create(user=student_b, cohort=cohort_1, role="STUDENT")
    CohortUser.objects.create(user=student_c, cohort=cohort_2, role="STUDENT")

    client.force_authenticate(user=staff.user)
    url = reverse_lazy("admissions:academy_cohort_id_report_csv", kwargs={"cohort_id": cohort_1.id})
    response = client.get(url, HTTP_ACADEMY=staff.academy.id)

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/csv")
    assert f'filename="cohort_{cohort_1.slug}_report.csv"' in response["Content-Disposition"]

    content = response.content.decode("utf-8")
    rows = list(csv.reader(StringIO(content)))

    assert rows[0] == [
        "course_name",
        "student_full_name",
        "student_email",
        "enrollment_date",
        "student_start_date",
        "status",
        "progress_percentage",
        "completion_date",
        "certificate_url",
        "comments",
    ]

    # Only rows for cohort_1 should be present
    assert len(rows[1:]) == 2
    assert all(r[0] == cohort_1.name for r in rows[1:])


def test_progress_report_returns_404_if_cohort_not_in_academy(database, client):
    from breathecode.admissions.models import Cohort
    from breathecode.authenticate.models import ProfileAcademy

    role = _setup_reporting_role(database)

    staff = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=staff.user, academy=staff.academy, role=role, email=staff.user.email)

    other = database.create(city=1, country=1, academy=1)
    other_cohort = Cohort.objects.create(
        slug="cohort-progress-other",
        name="Other Cohort",
        kickoff_date=timezone.now(),
        academy=other.academy,
    )

    client.force_authenticate(user=staff.user)
    url = reverse_lazy("admissions:academy_cohort_id_report_csv", kwargs={"cohort_id": other_cohort.id})
    response = client.get(url, HTTP_ACADEMY=staff.academy.id)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert data.get("status_code", 404) == 404

