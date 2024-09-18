# from django.db.models.signals import post_save
import logging
import re
from typing import Any, Type

from django.dispatch import receiver

import breathecode.authenticate.actions as authenticate_actions
from breathecode.assignments.models import Task
from breathecode.assignments.signals import revision_status_updated
from breathecode.certificate.actions import how_many_pending_tasks

from ..activity import tasks as activity_tasks
from .models import Cohort, CohortUser
from .signals import cohort_log_saved, cohort_user_created

# add your receives here
logger = logging.getLogger(__name__)
GITHUB_URL_PATTERN = re.compile(r"https?:\/\/github\.com\/(?P<user>[^\/]+)\/(?P<repo>[^\/\s]+)\/?")


@receiver(cohort_log_saved, sender=Cohort)
def process_cohort_history_log(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info("Processing Cohort history log for cohort: " + str(instance.id))

    activity_tasks.get_attendancy_log.delay(instance.id)


@receiver(cohort_user_created, sender=Cohort)
async def new_cohort_user(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info("Processing Cohort history log for cohort: " + str(instance.id))

    await authenticate_actions.send_webhook(
        "rigobot",
        "cohort_user.created",
        user=instance.user,
        data={
            "user": {
                "id": instance.user.id,
                "email": instance.user.email,
                "first_name": instance.user.first_name,
                "last_name": instance.user.last_name,
            },
        },
    )


@receiver(revision_status_updated, sender=Task, weak=False)
def schedule_repository_deletion(sender: Type[Task], instance: Task, **kwargs: Any):
    logger.info("Scheduling repository deletion for task: " + str(instance.id))

    if instance.revision_status != Task.RevisionStatus.PENDING and instance.github_url:
        match = GITHUB_URL_PATTERN.match(instance.github_url)
        if match:
            user = match.group("user")
            repo = match.group("repo")
            from breathecode.assignments.models import RepositoryDeletionOrder

            order, created = RepositoryDeletionOrder.objects.get_or_create(
                provider=RepositoryDeletionOrder.Provider.GITHUB,
                repository_user=user,
                repository_name=repo,
                defaults={"status": RepositoryDeletionOrder.Status.PENDING},
            )

            if not created and order.status in [
                RepositoryDeletionOrder.Status.NO_STARTED,
                RepositoryDeletionOrder.Status.ERROR,
            ]:
                order.status = RepositoryDeletionOrder.Status.PENDING
                order.save()


@receiver(revision_status_updated, sender=Task, weak=False)
def mark_saas_student_as_graduated(sender: Type[Task], instance: Task, **kwargs: Any):
    logger.info("Processing available as saas student's tasks and marking as GRADUATED if it is")

    if instance.cohort is None:
        return

    cohort = Cohort.objects.filter(id=instance.cohort.id).first()

    if not cohort.available_as_saas:
        return

    pending_tasks = how_many_pending_tasks(
        cohort.syllabus_version, instance.user, task_types=["PROJECT"], only_mandatory=True
    )

    if pending_tasks == 0:
        cohort_user = CohortUser.objects.filter(user=instance.user.id, cohort=cohort.id).first()
        cohort_user.educational_status = "GRADUATED"
        cohort_user.save()
