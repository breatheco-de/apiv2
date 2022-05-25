import logging
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Group

from breathecode.authenticate.models import ProfileAcademy
from .signals import profile_academy_saved

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def add_to_default_group(sender, instance: User, **kwargs):
    group = Group.objects.filter(name='Default').first()
    instance.groups.add(group)


@receiver(profile_academy_saved, sender=ProfileAcademy)
def post_save_profile_academy(sender, instance: ProfileAcademy, created: bool, **kwargs):
    if created and instance.user and instance.role.slug == 'student':
        group = Group.objects.filter(name='Student').first()
        instance.user.groups.add(group)
