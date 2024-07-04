import logging
from typing import Type

from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from task_manager.django.actions import schedule_task

from breathecode.admissions.models import CohortUser
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.authenticate import tasks
from breathecode.authenticate.models import ProfileAcademy, UserInvite
from breathecode.authenticate.signals import (
    cohort_user_deleted,
    invite_status_updated,
    user_info_deleted,
    user_info_updated,
)
from breathecode.mentorship.models import MentorProfile

from .tasks import async_add_to_organization, async_remove_from_organization

logger = logging.getLogger(__name__)


@receiver(post_save)
def update_user_group(sender, instance, created: bool, **_):
    # redirect to other signal to be able to mock it
    user_info_updated.send_robust(sender=sender, instance=instance, created=created)


@receiver(user_info_updated)
def set_user_group(sender, instance, created: bool, **_):
    group = None
    groups = None

    if not created:
        return

    # prevent errors with migrations
    try:
        if sender == User:
            group = Group.objects.filter(name="Default").first()
            groups = instance.groups

        is_valid_profile_academy = sender == ProfileAcademy and instance.user and instance.status == "ACTIVE"
        if is_valid_profile_academy and instance.role.slug == "student":
            group = Group.objects.filter(name="Student").first()
            groups = instance.user.groups

        if is_valid_profile_academy and instance.role.slug == "teacher":
            group = Group.objects.filter(name="Teacher").first()
            groups = instance.user.groups

        if sender == MentorProfile:
            group = Group.objects.filter(name="Mentor").first()
            groups = instance.user.groups

        if groups and group:
            groups.add(group)

    # this prevent a bug with migrations
    except ObjectDoesNotExist:
        pass


@receiver(post_delete)
def delete_user_group(sender, instance, **_):
    # redirect to other signal to be able to mock it
    user_info_deleted.send_robust(sender=sender, instance=instance)


@receiver(user_info_deleted)
def unset_user_group(sender, instance, **_):
    should_be_deleted = False
    group = None
    groups = None

    is_valid_profile_academy = sender == ProfileAcademy and instance.user and instance.status == "ACTIVE"
    if is_valid_profile_academy and instance.role.slug == "student":
        should_be_deleted = not ProfileAcademy.objects.filter(
            user=instance.user, role__slug="student", status="ACTIVE"
        ).exists()

        group = Group.objects.filter(name="Student").first()
        groups = instance.user.groups

    if is_valid_profile_academy and instance.role.slug == "teacher":
        should_be_deleted = not ProfileAcademy.objects.filter(
            user=instance.user, role__slug="teacher", status="ACTIVE"
        ).exists()

        group = Group.objects.filter(name="Teacher").first()
        groups = instance.user.groups

    if sender == MentorProfile:
        should_be_deleted = not MentorProfile.objects.filter(user=instance.user).exists()
        group = Group.objects.filter(name="Mentor").first()
        groups = instance.user.groups

    if should_be_deleted and groups and group:
        groups.remove(group)


@receiver(pre_delete, sender=CohortUser)
def delete_cohort_user(sender, instance, **_):
    cohort_user_deleted.send_robust(sender=sender, instance=instance)


@receiver(cohort_user_deleted, sender=CohortUser)
def post_delete_cohort_user(sender, instance, **_):

    # never ending cohorts cannot be in synch with github
    if instance.cohort.never_ends:
        return None

    logger.debug("Cohort user deleted, removing from organization")
    args = (instance.cohort.id, instance.user.id)
    kwargs = {"force": True}

    manager = schedule_task(async_remove_from_organization, "3w")
    if not manager.exists(*args, **kwargs):
        manager.call(*args, **kwargs)


@receiver(student_edu_status_updated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **_):

    logger.debug("User educational status updated to: " + str(instance.educational_status))
    if instance.educational_status == "ACTIVE":

        # never ending cohorts cannot be in synch with github
        if instance.cohort.never_ends:
            return None

        async_add_to_organization.delay(instance.cohort.id, instance.user.id)
    else:
        args = (instance.cohort.id, instance.user.id)

        manager = schedule_task(async_remove_from_organization, "3w")
        if not manager.exists(*args):
            manager.call(*args)


@receiver(invite_status_updated, sender=UserInvite)
def handle_invite_accepted(sender: Type[UserInvite], instance: UserInvite, **_):
    if (
        instance.status == "ACCEPTED"
        and not instance.user
        and User.objects.filter(email=instance.email).exists() is False
    ):
        tasks.create_user_from_invite.apply_async(args=[instance.id], countdown=60)
