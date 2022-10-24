import logging

from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone

from .models import Consumable
from .signals import (consume_service, grant_service_permissions, lose_service_permissions,
                      reimburse_service_units)

logger = logging.getLogger(__name__)


@receiver(consume_service, sender=Consumable)
def consume_service_receiver(sender, instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == -1:
        return

    instance.how_many -= how_many
    instance.save()

    if instance.how_many == 0:
        lose_service_permissions.send(instance=instance, sender=sender)


@receiver(reimburse_service_units, sender=Consumable)
def reimburse_service_units_receiver(sender, instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == -1:
        return

    grant_permissions = not instance.how_many and how_many

    instance.how_many += how_many
    instance.save()

    if grant_permissions:
        grant_service_permissions.send(instance=instance, sender=sender)


@receiver(lose_service_permissions, sender=Consumable)
def lose_service_permissions_receiver(sender, instance: Consumable, **kwargs):
    now = timezone.now()

    consumables = Consumable.objects.filter(Q(valid_until__lte=now) | Q(valid_until=None),
                                            user=instance.user,
                                            how_many=0)

    names = []

    for group in instance.groups.all():
        how_many = consumables.filter(service__groups__name=group.name).distinct().count()
        if how_many == 0:
            names.append(group.name)

    # lose the permissions
    instance.user.groups.filter(name_in=names).delete()


@receiver(grant_service_permissions, sender=Consumable)
def grant_service_permissions_receiver(sender, instance: Consumable, **kwargs):
    groups = instance.groups.all()

    for group in groups:
        if not instance.user.groups.filter(name=group.name).exists():
            instance.user.groups.add(group)
