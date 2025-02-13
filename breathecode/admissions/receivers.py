# from django.db.models.signals import post_save
import logging
import re
from typing import Any, Type
from asgiref.sync import sync_to_async

from django.dispatch import receiver

import breathecode.authenticate.actions as authenticate_actions
from breathecode.assignments.models import Task
from breathecode.assignments.signals import revision_status_updated
from breathecode.certificate.actions import how_many_pending_tasks

from ..activity import tasks as activity_tasks
from .models import Cohort, CohortUser
from .signals import cohort_log_saved, cohort_user_created, student_edu_status_updated

# add your receives here
logger = logging.getLogger(__name__)
GITHUB_URL_PATTERN = re.compile(r"https?:\/\/github\.com\/(?P<user>[^\/]+)\/(?P<repo>[^\/\s]+)\/?")
BREATHECODE_USERS = ["breatheco-de", "4GeeksAcademy", "4geeksacademy"]


@receiver(cohort_log_saved, sender=Cohort)
def process_cohort_history_log(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info("Processing Cohort history log for cohort: " + str(instance.id))

    activity_tasks.get_attendancy_log.delay(instance.id)


@sync_to_async
def join_to_micro_cohorts(cohort_user):

    micro_cohorts = cohort_user.cohort.micro_cohorts.all()

    user = cohort_user.user
    for cohort in micro_cohorts:
        micro_cohort_user = CohortUser.objects.filter(user=user, cohort=cohort, role=cohort_user.role).first()
        if micro_cohort_user is None:
            micro_cohort_user = CohortUser(
                user=user, cohort=cohort, role=cohort_user.role, finantial_status="FULLY_PAID"
            )
            micro_cohort_user.save()


@receiver(cohort_user_created, sender=CohortUser)
async def new_cohort_user(sender: Type[CohortUser], instance: CohortUser, **kwargs: Any):
    logger.info("Signal for created cohort user: " + str(instance.id))
    await join_to_micro_cohorts(instance)

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
    
    tasks.build_profile_academy.delay(instance.cohort.academy.id, instance.user.id, "student")


@receiver(revision_status_updated, sender=Task, weak=False)
def schedule_repository_deletion(sender: Type[Task], instance: Task, **kwargs: Any):
    from breathecode.assignments.models import RepositoryDeletionOrder

    logger.info("Scheduling repository deletion for task: " + str(instance.id))

    if instance.revision_status != Task.RevisionStatus.PENDING and instance.github_url:
        match = GITHUB_URL_PATTERN.match(instance.github_url)
        if match:
            user = match.group("user")
            repo = match.group("repo")

            if user not in BREATHECODE_USERS:
                return

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


@receiver(student_edu_status_updated, sender=CohortUser)
def post_save_cohort_user(sender: Type[CohortUser], instance: CohortUser, **kwargs: Any):
    logger.info("Validating if the student is graduating from a saas cohort")
    cohort = instance.cohort

    if instance.cohort is None:
        return

    if cohort.available_as_saas and instance.educational_status == "GRADUATED":
        # main_cohorts is the backwards relationship for the many to many
        # it contains every cohort that another cohort is linked to as a micro cohort
        main_cohorts = cohort.main_cohorts.all()
        for main in main_cohorts:
            main_cohort_user = CohortUser.objects.filter(cohort=main, user=instance.user).first()
            if main_cohort_user.educational_status != "GRADUATED":
                main_cohort = main_cohort_user.cohort
                micro_cohorts = main_cohort.micro_cohorts.all()
                cohort_users = CohortUser.objects.filter(user=instance.user, cohort__in=micro_cohorts).exclude(
                    educational_status__in=["GRADUATED"]
                )
                if len(cohort_users) == 0:
                    main_cohort_user.educational_status = "GRADUATED"
                    main_cohort_user.save()


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
