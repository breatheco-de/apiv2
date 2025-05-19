import logging
import os
import re
from typing import Any
from django.db.models import Q

from capyc.core.i18n import translation
from django.contrib.auth.models import User
from django.utils import timezone
from linked_services.django.service import Service
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

import breathecode.notify.actions as actions
from breathecode.admissions.models import CohortUser
from breathecode.assignments.actions import (
    NOTIFICATION_STRINGS,
    calculate_telemetry_indicator,
    validate_task_for_notifications,
)
from breathecode.assignments.models import AssignmentTelemetry, LearnPackWebhook
from breathecode.authenticate.actions import get_user_settings
from breathecode.notify import actions as notify_actions
from breathecode.services.learnpack import LearnPack
from breathecode.utils import TaskPriority

from .models import RepositoryDeletionOrder, Task

# Get an instance of a logger
logger = logging.getLogger(__name__)


@task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def student_task_notification(self, task_id, **_: Any):
    """Notify if the task was change."""
    logger.info("Starting student_task_notification")

    task = Task.objects.filter(id=task_id).first()
    if task is None:
        raise RetryTask("Task not found")

    validate_task_for_notifications(task)

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


@task(bind=True, priority=TaskPriority.ACTIVITY.value)
def async_learnpack_webhook(self, webhook_id, **_: Any):
    logger.info(f"Starting async_learnpack_webhook for webhook {webhook_id}")

    webhook = LearnPackWebhook.objects.filter(id=webhook_id).first()
    if webhook is None:
        message = f"Webhook {webhook_id} not found"

        raise RetryTask(message)

    try:
        client = LearnPack()
        client.execute_action(webhook_id)

    except Exception as e:
        webhook.status = "ERROR"
        webhook.status_text = str(e)
        webhook.save()
        raise e


@task(bind=True, priority=TaskPriority.NOTIFICATION.value)
def teacher_task_notification(self, task_id, **_: Any):
    """Notify if the task was change."""

    logger.info("Starting teacher_task_notification")

    url = os.getenv("TEACHER_URL")
    if not url:
        logger.error("TEACHER_URL is not set as environment variable")
        return

    url = re.sub("/$", "", url)

    task = Task.objects.filter(id=task_id).first()
    if task is None:
        raise RetryTask("Task not found")

    validate_task_for_notifications(task)

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


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def set_cohort_user_assignments(task_id: int, **_: Any):
    logger.info("Executing set_cohort_user_assignments")

    def serialize_task(task):
        return {
            "id": task.id,
            "type": task.task_type,
        }

    task = Task.objects.filter(id=task_id).first()

    if not task:
        raise AbortTask("Task not found")

    cohort_user = CohortUser.objects.filter(cohort=task.cohort, user=task.user, role="STUDENT").first()

    if not cohort_user:
        raise AbortTask("CohortUser not found")

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
    logger.info("History log saved")

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
        raise AbortTask(str(e))


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def sync_cohort_user_tasks(cohort_user_id: int, **_: Any):
    logger.info(f"Executing sync_cohort_user_tasks for cohort user {cohort_user_id}")
    cohort_user = CohortUser.objects.filter(id=cohort_user_id).first()

    if not cohort_user:
        logger.error("Cohort user not found")
        return

    cohort = cohort_user.cohort
    syllabus_json = cohort.syllabus_version.json

    all_cohort_tasks = []

    def parse_task(type, assignment):
        return {
            "task_type": type,
            "cohort": cohort.id,
            "user": cohort_user.user.id,
            "associated_slug": assignment["slug"],
            "title": assignment["title"],
        }

    for day in syllabus_json["days"]:

        readings = day["lessons"] if "lessons" in day else []
        replits = day["replits"] if "replits" in day else []
        assignments = day["assignments"] if "assignments" in day else []
        answers = day["quizzes"] if "quizzes" in day else []

        for r in readings:
            all_cohort_tasks.append(parse_task("LESSON", r))

        for r in replits:
            all_cohort_tasks.append(parse_task("EXERCISE", r))

        for r in assignments:
            all_cohort_tasks.append(parse_task("PROJECT", r))

        for r in answers:
            all_cohort_tasks.append(parse_task("QUIZ", r))

    for cohort_task in all_cohort_tasks:
        user_task = Task.objects.filter(
            user=cohort_user.user,
            cohort=cohort,
            associated_slug=cohort_task["associated_slug"],
            task_type=cohort_task["task_type"],
        ).first()

        if user_task is None:
            user_task = Task(
                user=cohort_user.user,
                cohort=cohort,
                associated_slug=cohort_task["associated_slug"],
                title=cohort_task["title"],
                task_type=cohort_task["task_type"],
            )
            user_task.save()

    logger.info(f"Cohort User {cohort_user_id} synced successfully")


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def send_repository_deletion_notification(deletion_order_id: int, new_owner: str, **_: Any):
    logger.info(f"Executing send_repository_deletion_notification for cohort user {deletion_order_id}")
    deletion_order = RepositoryDeletionOrder.objects.filter(
        id=deletion_order_id, status=RepositoryDeletionOrder.Status.TRANSFERRING, notified_at=None
    ).first()

    if deletion_order is None:
        raise RetryTask("Repository deletion order not found")

    if not new_owner:
        raise AbortTask("New owner not found")

    user = None
    link = None

    if deletion_order.provider == RepositoryDeletionOrder.Provider.GITHUB:
        user = User.objects.filter(credentialsgithub__username=new_owner).first()
        link = f"https://github.com/{deletion_order.repository_user}/{deletion_order.repository_name}"
    else:
        raise AbortTask(f"Provider {deletion_order.provider} not supported")

    if user is None:
        raise AbortTask(f"User not found for {RepositoryDeletionOrder.Provider.GITHUB} username {new_owner}")

    settings = get_user_settings(user.id)
    lang = settings.lang

    print(f"lang: {lang}")

    subject = translation(
        lang,
        en=f"We are transfering the repository {deletion_order.repository_name} to you",
        es=f"Te estamos transfiriendo el repositorio {deletion_order.repository_name}",
    )

    message = translation(
        lang,
        en=f"We are transfering the repository {deletion_order.repository_name} to you, you have two "
        "months to accept the transfer before we delete it",
        es=f"Te estamos transfiriendo el repositorio {deletion_order.repository_name}, tienes dos meses "
        "para aceptar la transferencia antes de que la eliminemos",
    )

    button = translation(
        lang,
        en="Go to the repository",
        es="Ir al repositorio",
    )

    notify_actions.send_email_message(
        "message",
        user.email,
        {
            "SUBJECT": subject,
            "MESSAGE": message,
            "BUTTON": button,
            "LINK": link,
        },
    )

    deletion_order.notified_at = timezone.now()
    deletion_order.save()


@task(bind=True, priority=TaskPriority.ACADEMY.value)
def async_calculate_telemetry_indicator(self, telemetry_id, **_: Any):
    telemetry = AssignmentTelemetry.objects.filter(id=telemetry_id).first()
    if telemetry:
        calculate_telemetry_indicator(telemetry)


@task(bind=True, priority=TaskPriority.ACADEMY.value)
def async_validate_flags(self, assignment_id: int, associated_slug: str, flags: str, **_: Any):
    """
    Validate CTF flags for an assignment submission.

    Args:
        assignment_id: The ID of the assignment submission
        asset_slug: The slug of the asset being validated
        flags: The flags to validate
    """
    logger.info(f"Starting async_validate_flags for assignment {assignment_id} and asset {associated_slug}")

    from breathecode.registry.models import Asset
    from .utils.flags import FlagManager

    # Get the assignment and asset
    assignment = Task.objects.filter(id=assignment_id).first()
    if not assignment:
        raise AbortTask(f"Assignment {assignment_id} not found")

    asset = Asset.objects.filter(Q(slug=associated_slug) | Q(assetalias__slug=associated_slug)).first()
    if not asset:
        raise AbortTask(f"Asset {associated_slug} not found")

    # Create a flag manager instance
    flag_manager = FlagManager()

    # Parse the comma-separated flags
    flag_list = flags.split(",") if isinstance(flags, str) else flags
    flag_list = [flag.strip() for flag in flag_list if flag.strip()]

    if "flags" not in asset.config["delivery"]["formats"]:
        raise AbortTask(f"Delivery of asset {associated_slug} is not expected to have flags, check the asset config")
    elif "quantity" not in asset.config["delivery"]:
        raise AbortTask(
            f"Missing quantity in the asset.config.delivery of {associated_slug}. How many flags are we expecting?"
        )

    if not flag_list:
        raise AbortTask(f"No flags provided for validation: {flags}")

    # Get the asset seed from the asset's flag_seed field
    if not asset.flag_seed:
        raise AbortTask(f"Asset {associated_slug} does not have a flag_seed")

    # Check for any revoked flags (if applicable)
    revoked_flags = []  # This could be populated from a database if needed

    # Validate each flag
    validation_results = []
    for flag in flag_list:
        try:
            is_valid = flag_manager.validate_flag(
                submitted_flag=flag, asset_seed=asset.flag_seed, revoked_flags=revoked_flags
            )
            validation_results.append(
                {"flag": flag, "is_valid": is_valid, "error": None if is_valid else "Invalid flag"}
            )
        except Exception as e:
            validation_results.append({"flag": flag, "is_valid": False, "error": str(e)})
            logger.error(f"Error validating flag '{flag}': {str(e)}")

    # Update the task with the validation results
    valid_flags = [result["flag"] for result in validation_results if result["is_valid"]]
    invalid_flags = [result["flag"] for result in validation_results if not result["is_valid"]]

    # Store the validated flags in the delivered_flags field
    if valid_flags:
        if assignment.delivered_flags is None:
            assignment.delivered_flags = {"approved": [], "rejected": []}

        # Add only new valid flags that aren't already in the list
        for flag in valid_flags:
            if flag not in assignment.delivered_flags:
                assignment.delivered_flags["approved"].append(flag)

        for flag in invalid_flags:
            if flag not in assignment.delivered_flags:
                assignment.delivered_flags["rejected"].append(flag)

    # Update the task description with validation results
    validation_summary = f"Flag validation results: {len(valid_flags)} valid, {len(invalid_flags)} invalid."
    if "Flag validation results:" not in assignment.description:
        assignment.description += f"\n\n{validation_summary}"
    else:
        # Replace existing validation results
        lines = assignment.description.split("\n")
        updated_lines = []
        for line in lines:
            if "Flag validation results:" in line:
                updated_lines.append(validation_summary)
            else:
                updated_lines.append(line)
        assignment.description = "\n".join(updated_lines)

    assignment.delivered_flags = valid_flags + invalid_flags
    if assignment.delivered_flags == asset.config["delivery"]["quantity"]:
        assignment.revision_status = "APPROVED"
    else:
        assignment.revision_status = "REJECTED"
        assignment.description = f'We are expecting {asset.config["delivery"]["quantity"]} valid flags, and you delivered the following: \n\n{validation_summary}'
    assignment.save()

    logger.info(f"Flag validation completed for assignment {assignment_id}: {assignment.revision_status}")
    return assignment.revision_status
