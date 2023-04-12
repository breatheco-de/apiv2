import logging

from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.admissions.models import CohortUser
from django.dispatch import receiver
from .tasks import async_remove_from_organization, async_add_to_organization
from breathecode.authenticate.models import ProfileAcademy
from breathecode.mentorship.models import MentorProfile

logger = logging.getLogger(__name__)


@receiver(post_save)
def set_user_group(sender, instance, created: bool, **kwargs):
    group = None
    groups = None

    if not created:
        return

    # prevent errors with migrations
    try:
        if sender == User:
            group = Group.objects.filter(name='Default').first()
            groups = instance.groups

        is_valid_profile_academy = sender == ProfileAcademy and instance.user and instance.status == 'ACTIVE'
        if is_valid_profile_academy and instance.role.slug == 'student':
            group = Group.objects.filter(name='Student').first()
            groups = instance.user.groups

        if is_valid_profile_academy and instance.role.slug == 'teacher':
            group = Group.objects.filter(name='Teacher').first()
            groups = instance.user.groups

        if sender == MentorProfile:
            group = Group.objects.filter(name='Mentor').first()
            groups = instance.user.groups

        if groups and group:
            groups.add(group)

    # this prevent a bug with migrations
    except ObjectDoesNotExist:
        pass


@receiver(post_delete)
def unset_user_group(sender, instance, **kwargs):
    should_be_deleted = False
    group = None
    groups = None

    is_valid_profile_academy = sender == ProfileAcademy and instance.user and instance.status == 'ACTIVE'
    if is_valid_profile_academy and instance.role.slug == 'student':
        should_be_deleted = not ProfileAcademy.objects.filter(
            user=instance.user, role__slug='student', status='ACTIVE').exists()

        group = Group.objects.filter(name='Student').first()
        groups = instance.user.groups

    if is_valid_profile_academy and instance.role.slug == 'teacher':
        should_be_deleted = not ProfileAcademy.objects.filter(
            user=instance.user, role__slug='teacher', status='ACTIVE').exists()

        group = Group.objects.filter(name='Teacher').first()
        groups = instance.user.groups

    if sender == MentorProfile:
        should_be_deleted = not MentorProfile.objects.filter(user=instance.user).exists()
        group = Group.objects.filter(name='Mentor').first()
        groups = instance.user.groups

    if should_be_deleted and groups and group:
        groups.remove(group)


@receiver(pre_delete, sender=CohortUser)
def post_delete_cohort_user(sender, instance, **kwargs):
    logger.debug('Cohort user deleted, removing from organization')
    async_remove_from_organization(instance.cohort.id, instance.user.id, force=True)


@receiver(student_edu_status_updated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **kwargs):
    logger.debug('User educational status updated to: ' + instance.educational_status)
    if instance.educational_status == 'ACTIVE':
        async_add_to_organization(instance.cohort.id, instance.user.id)
    else:
        async_remove_from_organization(instance.cohort.id, instance.user.id)
