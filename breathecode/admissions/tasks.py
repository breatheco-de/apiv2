import logging
import os
from typing import Any

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from task_manager.core.exceptions import AbortTask
from task_manager.django.decorators import task

import breathecode.activity.tasks as tasks_activity
from breathecode.authenticate.models import ProfileAcademy, Role
from breathecode.utils.decorators import TaskPriority

from .actions import test_syllabus
from .models import Academy, Cohort, CohortUser, SyllabusVersion

API_URL = os.getenv("API_URL", "")

logger = logging.getLogger(__name__)


@shared_task(priority=TaskPriority.ACADEMY.value)
def async_test_syllabus(syllabus_slug, syllabus_version) -> None:
    logger.debug("Process async_test_syllabus")

    syl_version = SyllabusVersion.objects.filter(syllabus__slug=syllabus_slug, version=syllabus_version).first()
    if syl_version is None:
        logger.error(f"Syllabus {syllabus_slug} v{syllabus_version} not found")

    syl_version.integrity_status = "PENDING"
    syl_version.integrity_check_at = timezone.now()
    try:
        report = test_syllabus(syl_version.json)
        syl_version.integrity_report = report.serialize()
        if report.http_status() == 200:
            syl_version.integrity_status = "OK"
        else:
            syl_version.integrity_status = "ERROR"

    except Exception as e:
        syl_version.integrity_report = {"errors": [str(e)], "warnings": []}
        syl_version.integrity_status = "ERROR"
    syl_version.save()


@task(priority=TaskPriority.STUDENT.value)
def build_cohort_user(cohort_id: int, user_id: int, role: str = "STUDENT", **_: Any) -> None:
    logger.info(f"Starting build_cohort_user for cohort {cohort_id} and user {user_id}")

    bad_stages = ["DELETED", "ENDED", "FINAL_PROJECT", "STARTED"]

    if not (cohort := Cohort.objects.filter(id=cohort_id).exclude(stage__in=bad_stages).first()):
        raise AbortTask(f"Cohort with id {cohort_id} not found")

    if not (user := User.objects.filter(id=user_id, is_active=True).first()):
        raise AbortTask(f"User with id {user_id} not found")

    cohort_user, created = CohortUser.objects.get_or_create(
        cohort=cohort,
        user=user,
        role=role,
        defaults={
            "finantial_status": "UP_TO_DATE",
            "educational_status": "ACTIVE",
        },
    )

    if created:
        logger.info("User added to cohort")

    if role == "TEACHER":
        role = "teacher"

    elif role == "ASSISTANT":
        role = "assistant"

    elif role == "REVIEWER":
        role = "homework_reviewer"

    else:
        role = "student"

    role = Role.objects.filter(slug=role).first()

    profile, created = ProfileAcademy.objects.get_or_create(
        academy=cohort.academy,
        user=user,
        role=role,
        defaults={
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": "ACTIVE",
        },
    )

    if profile.status != "ACTIVE":
        profile.status = "ACTIVE"
        profile.save()
        logger.info("ProfileAcademy mark as active")

    if created:
        logger.info("ProfileAcademy added")

    tasks_activity.add_activity.delay(
        user_id, "joined_cohort", related_type="admissions.CohortUser", related_id=cohort_user.id
    )


@task(priority=TaskPriority.STUDENT.value)
def build_profile_academy(academy_id: int, user_id: int, role: str = "student", **_: Any) -> None:
    logger.info(f"Starting build_profile_academy for cohort {academy_id} and user {user_id}")

    if not (user := User.objects.filter(id=user_id, is_active=True).first()):
        raise AbortTask(f"User with id {user_id} not found")

    if not (academy := Academy.objects.filter(id=academy_id).first()):
        raise AbortTask(f"Academy with id {academy_id} not found")

    if not (role := Role.objects.filter(slug=role).first()):
        raise AbortTask(f"Role with slug {role} not found")

    profile, created = ProfileAcademy.objects.get_or_create(
        academy=academy,
        user=user,
        role=role,
        defaults={
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": "ACTIVE",
        },
    )

    if profile.status != "ACTIVE":
        profile.status = "ACTIVE"
        profile.save()
        logger.info("ProfileAcademy mark as active")

    if created:
        logger.info("ProfileAcademy added")
