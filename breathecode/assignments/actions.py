import logging
import os

import requests

from breathecode.admissions.models import CohortUser
from capyc.rest_framework.exceptions import ValidationException

from .models import Task

logger = logging.getLogger(__name__)

HOST = os.environ.get("OLD_BREATHECODE_API")

NOTIFICATION_STRINGS = {
    "en": {
        "teacher": {
            "subject": "{first_name} {last_name} send their task",
            "details": '{first_name} {last_name} send their task "{title}", you can review the task at {url}',
        },
        "student": {
            "subject": 'Your task "{title}" has been reviewed',
            "PENDING": "Your task has been marked as pending",
            "APPROVED": "Your task has been marked as approved",
            "REJECTED": "Your task has been marked as rejected",
            "IGNORED": "Your task has been marked as ignored",
        },
    },
    "es": {
        "teacher": {
            "subject": "{first_name} {last_name} envió su tarea",
            "details": '{first_name} {last_name} envió su tarea "{title}", puedes revisarla en {url}',
        },
        "student": {
            "subject": 'Tu tarea "{title}" ha sido revisada',
            "PENDING": "Tu tarea se ha marcado como pendiente",
            "APPROVED": "Tu tarea se ha marcado como aprobada",
            "REJECTED": "Tu tarea se ha marcado como rechazada",
            "IGNORED": "Tu tarea se ha marcado como ignorada",
        },
    },
}


def deliver_task(github_url, live_url=None, task_id=None, task=None):

    if task is None:
        task = Task.objects.filter(id=task_id).first()
        if task is None:
            raise ValidationException("Invalid or missing task id")

    task.github_url = github_url
    task.live_url = live_url
    task.task_status = "DONE"
    task.revision_status = "PENDING"  # we have to make it pending so the teachers reviews again
    task.save()

    return task


# FIXME: this maybe is a deadcode
def sync_student_tasks(user, cohort=None):

    if cohort is None:
        cu = CohortUser.objects.filter(user=user).exclude(cohort__slug__contains="prework").first()
        if cu is not None:
            cohort = cu.cohort

    response = requests.get(f"{HOST}/student/{user.email}/task/", timeout=2)
    if response.status_code != 200:
        raise Exception(f"Student {user.email} not found on the old API")

    tasks = response.json()
    task_type = {
        "assignment": "PROJECT",
        "quiz": "QUIZ",
        "lesson": "LESSON",
        "replit": "EXERCISE",
    }

    revision_status = {
        "None": "PENDING",
        "pending": "PENDING",
        "approved": "APPROVED",
        "rejected": "REJECTED",
    }

    task_status = {
        "pending": "PENDING",
        "done": "DONE",
    }

    syncronized = []
    for _task in tasks["data"]:

        if _task["type"] not in task_type:
            raise Exception(f"Invalid task_type {_task['type']}")
        if _task["status"] not in task_status:
            raise Exception(f"Invalid status {_task['status']}")
        if str(_task["revision_status"]) not in revision_status:
            raise Exception(f"Invalid revision_status {_task['revision_status']}")

        task = Task.objects.filter(user_id=user.id, associated_slug=_task["associated_slug"]).first()
        if task is None:
            task = Task(
                user=user,
            )
            task.task_status = task_status[_task["status"]]
            task.live_url = _task["live_url"]
            task.github_url = _task["github_url"]
            task.associated_slug = _task["associated_slug"]
            task.title = _task["title"]
            task.task_type = task_type[_task["type"]]
            task.revision_status = revision_status[str(_task["revision_status"])]
            task.description = _task["description"]
            task.cohort = cohort
            task.save()
        syncronized.append(task)
    logger.debug(f"Added {len(syncronized)} tasks for student {user.email}")
    return syncronized


def sync_cohort_tasks(cohort):

    synchronized = []
    cohort_users = CohortUser.objects.filter(cohort__id=cohort.id, role="STUDENT", educational_status__in=["ACTIVE"])
    for cu in cohort_users:
        try:
            tasks = sync_student_tasks(cu.user, cohort=cohort)
            synchronized = synchronized + tasks
        except Exception:
            continue

    return synchronized


def task_is_valid_for_notifications(task: Task) -> bool:
    if not task:
        logger.error("Task not found")
        return False

    if not task.cohort:
        logger.error("Can't determine the student cohort")
        return False

    language = task.cohort.language.lower()

    if language not in NOTIFICATION_STRINGS:
        logger.error(f"The language {language} is not implemented in teacher_task_notification")
        return False

    return True
