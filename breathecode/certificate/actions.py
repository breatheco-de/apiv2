"""
Certificate actions
"""

import hashlib
import json
import logging
import os
from typing import Optional
from urllib.parse import urlencode

import requests
from django.contrib.auth.models import User
from django.utils import timezone

from breathecode.admissions.models import FULLY_PAID, UP_TO_DATE, CohortUser, SyllabusVersion
from breathecode.assignments.models import Task
from capyc.rest_framework.exceptions import ValidationException

from ..services.google_cloud import Storage
from .models import ERROR, PERSISTED, LayoutDesign, Specialty, UserSpecialty

logger = logging.getLogger(__name__)
ENVIRONMENT = os.getenv("ENV", None)
BUCKET_NAME = "certificates-breathecode"

strings = {
    "es": {
        "Main Instructor": "Instructor Principal",
    },
    "en": {
        "Main Instructor": "Main Instructor",
    },
}


def certificate_set_default_issued_at():
    query = UserSpecialty.objects.filter(status="PERSISTED", issued_at__isnull=True)

    for item in query:
        if item.cohort:

            UserSpecialty.objects.filter(id=item.id).update(issued_at=item.cohort.ending_date)

    return query


def syllabus_weeks_to_days(json):

    days = []
    weeks = json.pop("weeks", [])
    for week in weeks:
        days += week["days"]

    if "days" not in json:
        json["days"] = days

    return json


def get_assets_from_syllabus(
    syllabus_version: SyllabusVersion | int, task_types: Optional[list[str]] = None, only_mandatory=False
):
    if not isinstance(syllabus_version, SyllabusVersion):
        syllabus = SyllabusVersion.objects.filter(id=syllabus_version).first()

    else:
        syllabus = syllabus_version

    key_map = {
        "QUIZ": "quizzes",
        "LESSON": "lessons",
        "EXERCISE": "replits",
        "PROJECT": "assignments",
    }

    if task_types is None:
        task_types = key_map.keys()

    findings = []

    if isinstance(syllabus.json, str):
        syllabus.json = json.loads(syllabus.json)

    syllabus.json = syllabus_weeks_to_days(syllabus.json)

    for day in syllabus.json["days"]:
        for atype in key_map:
            if key_map[atype] not in day:
                continue

            if atype not in task_types:
                continue

            for asset in day[key_map[atype]]:
                if (only_mandatory and asset.get("mandatory", True) == True) or only_mandatory is False:
                    findings.append(asset["slug"])

    return findings


def how_many_pending_tasks(
    syllabus_version: SyllabusVersion | int, user: User | int, task_types: list[str], only_mandatory: bool
) -> int:

    extra = {}
    if (n_task_types := len(task_types)) == 1:

        extra["task_type"] = task_types[0]

    elif n_task_types > 1:
        extra["task_type__in"] = task_types

    if not isinstance(user, User):
        extra["user__id"] = user.id

    else:
        extra["user"] = user

    slugs = get_assets_from_syllabus(syllabus_version, task_types=task_types, only_mandatory=only_mandatory)
    how_many_approved_tasks = Task.objects.filter(
        associated_slug__in=slugs, revision_status__in=["APPROVED", "IGNORED"], **extra
    ).count()

    how_many_pending_tasks = (
        Task.objects.filter(associated_slug__in=slugs, **extra)
        .exclude(revision_status__in=["APPROVED", "IGNORED"])
        .count()
    )

    how_many_tasks = how_many_approved_tasks + how_many_pending_tasks
    if (how_many_slugs := len(slugs)) != how_many_tasks:
        how_many_pending_tasks = how_many_slugs - how_many_approved_tasks

    return how_many_pending_tasks


def generate_certificate(user, cohort=None, layout=None):
    query = {"user__id": user.id}

    if cohort:
        query["cohort__id"] = cohort.id

    cohort_user = CohortUser.objects.filter(**query).exclude(cohort__stage="DELETED").first()

    if not cohort_user:
        raise ValidationException(
            "Impossible to obtain the student cohort, maybe it's none assigned", slug="missing-cohort-user"
        )

    if not cohort:
        cohort = cohort_user.cohort

    if cohort.syllabus_version is None:
        raise ValidationException(
            f"The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}",
            slug="missing-syllabus-version",
        )

    specialty = Specialty.objects.filter(syllabus__id=cohort.syllabus_version.syllabus_id).first()
    if not specialty:
        raise ValidationException("Specialty has no Syllabus assigned", slug="missing-specialty")

    uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()

    if uspe is not None and uspe.status == "PERSISTED" and uspe.preview_url:
        raise ValidationException("This user already has a certificate created", slug="already-exists")

    if uspe is None:
        utc_now = timezone.now()
        uspe = UserSpecialty(
            user=user,
            cohort=cohort,
            token=hashlib.sha1((str(user.id) + str(utc_now)).encode("UTF-8")).hexdigest(),
            specialty=specialty,
            signed_by_role=strings[cohort.language.lower()]["Main Instructor"],
        )
        if specialty.expiration_day_delta is not None:
            uspe.expires_at = utc_now + timezone.timedelta(days=specialty.expiration_day_delta)

    layout = LayoutDesign.objects.filter(slug=layout).first()

    if layout is None:
        layout = LayoutDesign.objects.filter(is_default=True, academy=cohort.academy).first()

    if layout is None:
        layout = LayoutDesign.objects.filter(slug="default").first()

    if layout is None:
        raise ValidationException(
            "No layout was specified and there is no default layout for this academy", slug="no-default-layout"
        )

    uspe.layout = layout

    # validate for teacher
    main_teacher = CohortUser.objects.filter(cohort__id=cohort.id, role="TEACHER").first()
    if main_teacher is None or main_teacher.user is None:
        raise ValidationException(
            "This cohort does not have a main teacher, please assign it first", slug="without-main-teacher"
        )

    main_teacher = main_teacher.user
    uspe.signed_by = main_teacher.first_name + " " + main_teacher.last_name

    try:
        uspe.academy = cohort.academy
        pending_tasks = how_many_pending_tasks(
            cohort.syllabus_version, user, task_types=["PROJECT"], only_mandatory=True
        )

        if pending_tasks and pending_tasks > 0:
            raise ValidationException(
                f"The student has {pending_tasks} pending tasks", slug=f"with-pending-tasks-{pending_tasks}"
            )

        if not (cohort_user.finantial_status == FULLY_PAID or cohort_user.finantial_status == UP_TO_DATE):
            message = "The student must have finantial status FULLY_PAID or UP_TO_DATE"
            raise ValidationException(message, slug="bad-finantial-status")

        if cohort_user.educational_status != "GRADUATED":
            raise ValidationException(
                "The student must have educational " "status GRADUATED", slug="bad-educational-status"
            )

        if not cohort.never_ends and cohort.current_day != cohort.syllabus_version.syllabus.duration_in_days:
            raise ValidationException(
                "Cohort current day should be " f"{cohort.syllabus_version.syllabus.duration_in_days}",
                slug="cohort-not-finished",
            )

        if not cohort.never_ends and cohort.stage != "ENDED":
            raise ValidationException(
                "The student cohort stage has to be 'ENDED' before you can issue any certificates",
                slug="cohort-without-status-ended",
            )

        if not uspe.issued_at:
            uspe.issued_at = timezone.now()

        uspe.status = PERSISTED
        uspe.status_text = "Certificate successfully queued for PDF generation"
        uspe.save()

    except ValidationException as e:
        message = str(e)
        uspe.status = ERROR
        uspe.status_text = message
        uspe.save()

    return uspe


def certificate_screenshot(certificate_id: int):

    certificate = UserSpecialty.objects.get(id=certificate_id)
    if not certificate.preview_url:
        file_name = f"{certificate.token}"

        storage = Storage()
        file = storage.file(BUCKET_NAME, file_name)

        # if the file does not exist
        if file.blob is None:
            query_string = urlencode(
                {
                    "key": os.environ.get("SCREENSHOT_MACHINE_KEY"),
                    "url": f"https://certificate.4geeks.com/preview/{certificate.token}",
                    "device": "desktop",
                    "cacheLimit": "0",
                    "dimension": "1024x707",
                }
            )
            r = requests.get(f"https://api.screenshotmachine.com?{query_string}", stream=True)
            if r.status_code == 200:
                file.upload(r.content, public=True)
            else:
                print("Invalid reponse code: ", r.status_code)

        # after created, lets save the URL
        if file.blob is not None:
            certificate.preview_url = file.url()
            certificate.save()


def remove_certificate_screenshot(certificate_id):
    certificate = UserSpecialty.objects.get(id=certificate_id)
    if not certificate.preview_url:
        return False

    file_name = certificate.token
    storage = Storage()
    file = storage.file(BUCKET_NAME, file_name)
    file.delete()

    certificate.preview_url = ""
    certificate.save()

    return True
