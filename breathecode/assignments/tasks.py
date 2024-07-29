import logging
import os
import re

from celery import shared_task
from linked_services.django.service import Service

import breathecode.notify.actions as actions
from breathecode.services.learnpack import LearnPack
from breathecode.admissions.models import CohortUser
from breathecode.assignments.models import LearnPackWebhook
from breathecode.assignments.actions import NOTIFICATION_STRINGS, task_is_valid_for_notifications
from breathecode.utils import TaskPriority

from .models import Task

# Get an instance of a logger
logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def student_task_notification(self, task_id):
    """Notify if the task was change."""
    logger.info("Starting student_task_notification")

    task = Task.objects.filter(id=task_id).first()
    if not task_is_valid_for_notifications(task):
        return

    language = task.cohort.language.lower()
    revision_status = task.revision_status
    subject = NOTIFICATION_STRINGS[language]["student"]["subject"].format(title=task.title)
    details = NOTIFICATION_STRINGS[language]["student"][revision_status]

    academy = None
    if task.cohort:
        academy = task.cohort.academy

    actions.send_email_message(
        "diagnostic",
        task.user.email,
        {
            "subject": subject,
            "details": details,
        },
        academy=academy,
    )


@shared_task(bind=True, priority=TaskPriority.ACTIVITY.value)
def async_learnpack_webhook(self, webhook_id):
    logger.debug("Starting async_learnpack_webhook")
    status = "ok"

    webhook = LearnPackWebhook.objects.filter(id=webhook_id).first()
    if webhook:
        try:
            client = LearnPack()
            client.execute_action(webhook_id)
        except Exception as e:
            logger.debug("LearnPack Telemetry exception")
            logger.debug(str(e))
            status = "error"

    else:
        message = f"Webhook {webhook_id} not found"
        webhook.status = "ERROR"
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = "error"

    logger.debug(f"LearnPack telemetry status: {status}")


@shared_task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def teacher_task_notification(self, task_id):
    """Notify if the task was change."""

    logger.info("Starting teacher_task_notification")

    url = os.getenv("TEACHER_URL")
    if not url:
        logger.error("TEACHER_URL is not set as environment variable")
        return

    url = re.sub("/$", "", url)

    task = Task.objects.filter(id=task_id).first()
    if not task_is_valid_for_notifications(task):
        return

    language = task.cohort.language.lower()
    subject = NOTIFICATION_STRINGS[language]["teacher"]["subject"].format(
        first_name=task.user.first_name, last_name=task.user.last_name
    )

    details = NOTIFICATION_STRINGS[language]["teacher"]["details"].format(
        first_name=task.user.first_name,
        last_name=task.user.last_name,
        title=task.title,
        url=f"{url}/cohort/{task.cohort.slug}/assignments",
    )

    academy = None
    if task.cohort:
        academy = task.cohort.academy

    actions.send_email_message(
        "diagnostic",
        task.user.email,
        {
            "subject": subject,
            "details": details,
        },
        academy=academy,
    )


@shared_task(bind=False, priority=TaskPriority.ACADEMY.value)
def set_cohort_user_assignments(task_id: int):
    logger.info("Executing set_cohort_user_assignments")

    def serialize_task(task):
        return {
            "id": task.id,
            "type": task.task_type,
        }

    task = Task.objects.filter(id=task_id).first()

    if not task:
        logger.error("Task not found")
        return

    cohort_user = CohortUser.objects.filter(cohort=task.cohort, user=task.user, role="STUDENT").first()

    if not cohort_user:
        logger.error("CohortUser not found")
        return

    user_history_log = cohort_user.history_log or {}
    user_history_log["delivered_assignments"] = user_history_log.get("delivered_assignments", [])
    user_history_log["pending_assignments"] = user_history_log.get("pending_assignments", [])

    user_history_log["pending_assignments"] = [x for x in user_history_log["pending_assignments"] if x["id"] != task.id]

    user_history_log["delivered_assignments"] = [
        x for x in user_history_log["delivered_assignments"] if x["id"] != task.id
    ]

    if task.task_status == "PENDING":
        user_history_log["pending_assignments"].append(serialize_task(task))

    if task.task_status == "DONE":
        user_history_log["delivered_assignments"].append(serialize_task(task))

    cohort_user.history_log = user_history_log
    cohort_user.save()

    s = None
    try:
        if hasattr(task.user, "credentialsgithub") and task.github_url:
            with Service("rigobot", task.user.id) as s:
                if task.task_status == "DONE":
                    response = s.post(
                        "/v1/finetuning/me/repository/",
                        json={
                            "url": task.github_url,
                            "watchers": task.user.credentialsgithub.username,
                        },
                    )
                    data = response.json()
                    task.rigobot_repository_id = data["id"]

                else:
                    response = s.put(
                        "/v1/finetuning/me/repository/",
                        json={
                            "url": task.github_url,
                            "activity_status": "INACTIVE",
                        },
                    )

                    data = response.json()
                    task.rigobot_repository_id = data["id"]

    except Exception as e:
        logger.error(str(e))

    logger.info("History log saved")
