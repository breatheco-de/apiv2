# from django.db.models.signals import post_save
import logging
import re
from typing import Any, Type

from asgiref.sync import sync_to_async
from django.dispatch import receiver

from breathecode.admissions import tasks
from breathecode.assignments.models import Task
from breathecode.assignments.signals import revision_status_updated
from breathecode.certificate.actions import how_many_pending_tasks, get_assets_from_syllabus

from ..activity import tasks as activity_tasks
from .models import Academy, Cohort, CohortUser, Syllabus, SyllabusVersion
from .signals import (
    academy_saved,
    cohort_log_saved,
    cohort_user_created,
    micro_cohorts_added,
    student_edu_status_updated,
    syllabus_created,
)

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

    # await authenticate_actions.send_webhook(
    #     "rigobot",
    #     "cohort_user.created",
    #     user=instance.user,
    #     data={
    #         "user": {
    #             "id": instance.user.id,
    #             "email": instance.user.email,
    #             "first_name": instance.user.first_name,
    #             "last_name": instance.user.last_name,
    #         },
    #     },
    # )

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
                user=instance.user,
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
    logger.info(
        "[graduate] start | task_id=%s user_id=%s cohort_id=%s",
        getattr(instance, "id", None),
        getattr(instance.user, "id", None),
        getattr(instance.cohort, "id", None),
    )

    if instance.cohort is None:
        logger.info("[graduate] task has no cohort -> return")
        return

    cohort = Cohort.objects.filter(id=instance.cohort.id).first()
    if cohort is None:
        logger.info("[graduate] cohort not found (id=%s) -> return", getattr(instance.cohort, "id", None))
        return

    logger.info(
        "[graduate] cohort id=%s available_as_saas=%s syllabus_version=%s",
        cohort.id,
        cohort.available_as_saas,
        getattr(cohort, "syllabus_version_id", None),
    )

    if not cohort.available_as_saas:
        logger.info("[graduate] cohort is not SaaS -> return")
        return

    mandatory_projects = get_assets_from_syllabus(cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True)
    logger.info(
        "[graduate] mandatory_projects_count=%s mandatory_projects=%s",
        len(mandatory_projects),
        mandatory_projects,
    )

    # Only graduate students if the syllabus has mandatory projects
    if len(mandatory_projects) == 0:
        logger.info("[graduate] no mandatory projects in syllabus -> return")
        return

    pending_tasks = how_many_pending_tasks(
        cohort.syllabus_version,
        instance.user,
        task_types=["PROJECT"],
        only_mandatory=True,
        cohort_id=cohort.id,
    )
    logger.info("[graduate] pending_tasks=%s", pending_tasks)

    try:
        user_tasks = list(
            Task.objects.filter(user=instance.user, associated_slug__in=mandatory_projects).values(
                "associated_slug", "revision_status", "task_status"
            )
        )
        logger.info("[graduate] user_tasks_snapshot=%s", user_tasks)
    except Exception as e:
        logger.warning("[graduate] unable to fetch user tasks snapshot: %s", str(e))

    if pending_tasks == 0:
        cohort_user = CohortUser.objects.filter(user=instance.user.id, cohort=cohort.id).first()
        if cohort_user is None:
            logger.info(
                "[graduate] CohortUser not found for user_id=%s cohort_id=%s -> return",
                instance.user.id,
                cohort.id,
            )
            return

        before_status = cohort_user.educational_status
        cohort_user.educational_status = "GRADUATED"
        cohort_user.save()
        logger.info(
            "[graduate] educational_status changed %s -> %s for cohort_user_id=%s",
            before_status,
            cohort_user.educational_status,
            cohort_user.id,
        )
    else:
        logger.info("[graduate] there are still mandatory pending tasks -> do not graduate")


@receiver(syllabus_created, sender=Syllabus)
def create_initial_syllabus_version(sender: Type[Syllabus], instance: Syllabus, **kwargs: Any):
    """Create an initial SyllabusVersion when a new Syllabus is created."""
    logger.info(f"Creating initial SyllabusVersion for Syllabus: {instance.id}")

    # Create the first version (version 1) with default JSON
    SyllabusVersion.objects.create(syllabus=instance, version=1, status="PUBLISHED")


@receiver(academy_saved, sender=Academy)
def create_owner_profile_academy(sender: Type[Academy], instance: Academy, created: bool, **kwargs: Any):
    """
    When an academy is created with an owner, automatically create a ProfileAcademy
    with admin role for that owner.

    This ensures the owner can manage the academy they created.
    """
    if created and instance.owner:
        from breathecode.authenticate.models import ProfileAcademy, Role

        logger.info(f"Creating ProfileAcademy for academy owner: {instance.slug} -> {instance.owner.email}")

        admin_role = Role.objects.filter(slug="admin").first()
        if not admin_role:
            logger.warning(f"Admin role not found, cannot create ProfileAcademy for academy {instance.slug}")
            return

        profile_academy, created_profile = ProfileAcademy.objects.get_or_create(
            user=instance.owner,
            academy=instance,
            defaults={
                "email": instance.owner.email,
                "role": admin_role,
                "first_name": instance.owner.first_name,
                "last_name": instance.owner.last_name,
                "status": "ACTIVE",
            },
        )

        if created_profile:
            logger.info(f"Created ProfileAcademy for {instance.owner.email} at {instance.slug}")
        else:
            logger.info(f"ProfileAcademy already exists for {instance.owner.email} at {instance.slug}")


@receiver(micro_cohorts_added, sender=Cohort)
def update_payment_plans_when_micro_cohorts_added(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    """
    Receiver that triggers when micro-cohorts are added to a cohort.
    This updates all payment plans that include the cohort to also include the new micro-cohorts.
    """
    logger.info(f"Micro-cohorts were added to cohort {instance.id} ({instance.slug}), updating payment plans")

    from breathecode.payments import tasks as payment_tasks

    payment_tasks.update_payment_plans_with_micro_cohorts.delay(instance.id)
