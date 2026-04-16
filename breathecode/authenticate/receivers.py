import logging
from typing import Type

from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from task_manager.django.actions import schedule_task

from breathecode.admissions.models import CohortUser
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.authenticate import tasks
from breathecode.payments.models import Service
from breathecode.payments.models import Consumable
from breathecode.payments.signals import grant_service_permissions
from breathecode.authenticate.models import ADD, GithubAcademyUser, ProfileAcademy, SYNCHED, UserInvite
from breathecode.authenticate.signals import (
    cohort_user_deleted,
    invite_status_updated,
    invite_email_validated,
    user_info_deleted,
    user_info_updated,
    profile_academy_role_changed,
)
from breathecode.mentorship.models import MentorProfile
from breathecode.payments.models import SubscriptionSeat

from .tasks import async_add_to_organization, async_remove_from_organization

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
@receiver(post_save, sender=ProfileAcademy)
@receiver(post_save, sender=MentorProfile)
@receiver(post_save, sender=SubscriptionSeat)
def update_user_group(sender, instance, created: bool, **_):
    # redirect to other signal to be able to mock it
    user_info_updated.send_robust(sender=sender, instance=instance, created=created)


@receiver(user_info_updated)
def set_user_group(sender, instance, created: bool, **_):
    from breathecode.payments import actions as payments_actions

    group = None
    groups = None

    # Only run on creation for most models
    if not created:
        # Special case: For ProfileAcademy, also run when status changes to ACTIVE
        # This handles the two-step creation pattern: create as INVITED, then update to ACTIVE
        if sender == ProfileAcademy:
            # Check if status just changed to ACTIVE (handles two-step invite acceptance)
            status_changed_to_active = (
                hasattr(instance, "_ProfileAcademy__old_status")
                and instance._ProfileAcademy__old_status != "ACTIVE"
                and instance.status == "ACTIVE"
            )
            if not status_changed_to_active:
                return
        elif sender == SubscriptionSeat:
            if not getattr(instance, "user", None):
                return
        else:
            return

    # prevent errors with migrations
    try:
        if sender == SubscriptionSeat and instance.user:
            group = Group.objects.filter(name="Student").first()
            groups = instance.user.groups

            # Only grant capabilities when the user is missing the Student group.
            # This keeps the fix focused and avoids heavy re-processing on every seat update.
            if group and not instance.user.groups.filter(name="Student").exists():
                for plan in instance.billing_team.plans.all():
                    payments_actions.grant_student_capabilities(instance.user, plan)

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

        if is_valid_profile_academy and instance.role.slug == "geek_creator":
            group = Group.objects.filter(name="Geek Creator").first()
            groups = instance.user.groups

        if sender == MentorProfile:
            group = Group.objects.filter(name="Mentor").first()
            groups = instance.user.groups

        if groups and group:
            # Use add() which is idempotent - won't duplicate if already in group
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

    if is_valid_profile_academy and instance.role.slug == "geek_creator":
        should_be_deleted = not ProfileAcademy.objects.filter(
            user=instance.user, role__slug="geek_creator", status="ACTIVE"
        ).exists()

        group = Group.objects.filter(name="Geek Creator").first()
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


@receiver(profile_academy_role_changed)
def handle_profile_academy_role_change(instance, old_role, new_role, **kwargs):
    """
    Handle group changes when ProfileAcademy role changes between student, teacher, and teacher_influencer.
    This ensures proper group transitions when switching between these main roles.
    """
    if not instance.user:
        return

    main_roles = ["student", "teacher", "geek_creator"]

    if not (old_role and new_role and (old_role.slug in main_roles or new_role.slug in main_roles)):
        return

    role_group_mapping = {
        "student": "Student",
        "teacher": "Teacher",
        "geek_creator": "Geek Creator",
    }

    old_group_name = role_group_mapping.get(old_role.slug)
    new_group_name = role_group_mapping.get(new_role.slug)

    if not old_group_name or not new_group_name:
        return

    old_group = Group.objects.filter(name=old_group_name).first()
    if old_group and old_group in instance.user.groups.all():
        instance.user.groups.remove(old_group)
        logger.info(
            f"Removed user {instance.user.id} from group {old_group_name} (role changed from {old_role.slug} to {new_role.slug})"
        )

    new_group = Group.objects.filter(name=new_group_name).first()
    if new_group and new_group not in instance.user.groups.all():
        instance.user.groups.add(new_group)
        logger.info(
            f"Added user {instance.user.id} to group {new_group_name} (role changed from {old_role.slug} to {new_role.slug})"
        )


@receiver(invite_email_validated, sender=UserInvite)
def sync_email_validation_across_invites(sender, instance, **kwargs):
    """
    When an invite's email is validated, automatically validate all other invites with the same email.
    This ensures consistency across all invites for the same email address.

    This receiver is triggered by the custom signal 'invite_email_validated' which is sent
    from the UserInvite model when is_email_validated changes from False to True.
    """
    if not instance.email:
        return

    other_invites = UserInvite.objects.filter(email=instance.email, is_email_validated=False).exclude(id=instance.id)

    if not other_invites.exists():
        return

    updated_count = other_invites.update(
        is_email_validated=True, email_quality=instance.email_quality, email_status=instance.email_status
    )

    logger.info(
        f"Email validation synced: {updated_count} invites with email '{instance.email}' "
        f"were automatically validated based on invite {instance.id}"
    )


@receiver(grant_service_permissions, sender=Consumable)
def provision_github_copilot_on_service_granted(sender, instance: Consumable, **kwargs):
    service = getattr(instance.service_item, "service", None)
    if not service:
        return

    if getattr(service, "consumer", None) != Service.Consumer.GITHUB_COPILOT:
        return

    user = instance.subscription_seat.user if instance.subscription_seat else instance.user
    if not user:
        return

    academy_id = None
    if instance.subscription and instance.subscription.academy_id:
        academy_id = instance.subscription.academy_id
    elif instance.plan_financing and instance.plan_financing.academy_id:
        academy_id = instance.plan_financing.academy_id

    logger.info(
        "[COPILOT grant_service_permissions] consumable_id=%s user_id=%s academy_id=%s slug=%s -> provision task",
        instance.id,
        user.id,
        academy_id,
        service.slug,
    )
    tasks.provision_github_copilot_task.delay(user.id, academy_id=academy_id)


@receiver(pre_save, sender=GithubAcademyUser)
def github_academy_user_copilot_track_prev(sender, instance: GithubAcademyUser, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields and set(update_fields).issubset({"storage_log", "updated_at"}):
        return

    if not instance.pk:
        instance._copilot_prev_good = False
        logger.info(
            "[COPILOT GithubAcademyUser pre_save] new row academy_id=%s user_id=%s action=%s status=%s",
            instance.academy_id,
            instance.user_id,
            instance.storage_action,
            instance.storage_status,
        )
        return
    prev = GithubAcademyUser.objects.filter(pk=instance.pk).only("storage_status", "storage_action").first()
    instance._copilot_prev_good = bool(
        prev and prev.storage_status == SYNCHED and prev.storage_action == ADD
    )
    logger.info(
        "[COPILOT GithubAcademyUser pre_save] id=%s prev_good=%s -> new action=%s status=%s",
        instance.pk,
        instance._copilot_prev_good,
        instance.storage_action,
        instance.storage_status,
    )


@receiver(post_save, sender=GithubAcademyUser)
def github_academy_user_copilot_react(sender, instance: GithubAcademyUser, created: bool, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields and set(update_fields).issubset({"storage_log", "updated_at"}):
        return

    if not instance.user_id:
        return

    prev_good = getattr(instance, "_copilot_prev_good", False)
    now_good = instance.storage_status == SYNCHED and instance.storage_action == ADD

    if prev_good and not now_good:
        args = (instance.user_id, instance.academy_id)
        manager = schedule_task(tasks.deferred_github_copilot_remove_if_still_revoked, "2h")
        if manager.exists(*args):
            logger.info(
                "[COPILOT GithubAcademyUser post_save] id=%s user_id=%s academy_id=%s lost_eligibility -> deferred revoke 2h already_scheduled",
                instance.id,
                instance.user_id,
                instance.academy_id,
            )
            return
        async_result = manager.call(*args)
        logger.info(
            "[COPILOT GithubAcademyUser post_save] id=%s user_id=%s academy_id=%s lost_eligibility -> deferred revoke 2h task_id=%s",
            instance.id,
            instance.user_id,
            instance.academy_id,
            getattr(async_result, "id", None),
        )
    elif now_good and (created or not prev_good):
        async_result = tasks.provision_github_copilot_task.delay(instance.user_id, academy_id=instance.academy_id)
        logger.info(
            "[COPILOT GithubAcademyUser post_save] id=%s user_id=%s academy_id=%s eligible -> provision task_id=%s",
            instance.id,
            instance.user_id,
            instance.academy_id,
            async_result.id,
        )
