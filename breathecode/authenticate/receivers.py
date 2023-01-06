import logging

from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

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
