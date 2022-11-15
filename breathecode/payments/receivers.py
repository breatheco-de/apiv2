import logging
import re
from typing import Type

from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from django.db.models.signals import post_delete, post_save

from breathecode.admissions.models import Cohort
from breathecode.payments.actions import get_fixture_patterns

from .models import Consumable, Fixture
from .signals import (consume_service, grant_service_permissions, lose_service_permissions,
                      reimburse_service_units)

logger = logging.getLogger(__name__)


@receiver(consume_service, sender=Consumable)
def consume_service_receiver(sender: Type[Consumable], instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == 0:
        lose_service_permissions.send(instance=instance, sender=sender)
        return

    if instance.how_many == -1:
        return

    instance.how_many -= how_many
    instance.save()

    if instance.how_many == 0:
        lose_service_permissions.send(instance=instance, sender=sender)


@receiver(reimburse_service_units, sender=Consumable)
def reimburse_service_units_receiver(sender: Type[Consumable], instance: Consumable, how_many: float,
                                     **kwargs):
    if instance.how_many == -1:
        return

    grant_permissions = not instance.how_many and how_many

    instance.how_many += how_many
    instance.save()

    if grant_permissions:
        grant_service_permissions.send(instance=instance, sender=sender)


@receiver(lose_service_permissions, sender=Consumable)
def lose_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    now = timezone.now()

    if instance.how_many != 0:
        return

    consumables = Consumable.objects.filter(Q(valid_until__lte=now) | Q(valid_until=None),
                                            user=instance.user).exclude(how_many=0)

    # for group in instance.user.groups.all():
    for group in instance.service_item.service.groups.all():
        # if group ==
        how_many = consumables.filter(service_item__service__groups__name=group.name).distinct().count()
        if how_many == 0:
            instance.user.groups.remove(group)


@receiver(grant_service_permissions, sender=Consumable)
def grant_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    groups = instance.groups.all()

    for group in groups:
        if not instance.user.groups.filter(name=group.name).exists():
            instance.user.groups.add(group)


@receiver(post_save, sender=Cohort)
def manage_fixture_related_to_cohort_on_save(sender: Type[Cohort], instance: Cohort, **kwargs):
    cache = {}
    # the fixtures are only for the upcoming cohorts
    if instance.ending_date and instance.ending_date < timezone.now():
        return

    if instance.stage not in ['INACTIVE', 'PREWORK', 'DELETED']:
        return

    fixtures = get_fixture_patterns(instance.academy.id)
    for fixture in fixtures:
        if fixture['cohort'] == None:
            return

        if re.findall(fixture['cohort'], instance.slug):
            if 'id' not in fixture:
                cache[fixture['id']] = Fixture.objects.filter(id=fixture['id']).first()
            else:
                cache[fixture['id']] = cache.get(fixture['id'])

            if instance.stage == 'DELETED':
                cache[fixture['id']].cohorts.remove(instance)

            else:
                cache[fixture['id']].cohorts.add(instance)


@receiver(post_save, sender=Fixture)
def clear_fixture_cache_on_save(sender: Type[Fixture], instance: Fixture, **kwargs):
    get_fixture_patterns.cache_clear()


@receiver(post_delete, sender=Fixture)
def clear_fixture_cache_on_delete(sender: Type[Fixture], instance: Fixture, **kwargs):
    get_fixture_patterns.cache_clear()


@receiver(post_save, sender=Fixture)
def seed_fixture_on_save(sender: Type[Fixture], instance: Fixture, created: bool, **kwargs):
    if instance.cohort_pattern:
        cohorts = Cohort.objects.filter(slug__regex=instance.cohort_pattern).values_list('id', flat=True)

        for cohort in cohorts:
            if not created and instance.cohorts.filter(id=cohort).exists():
                continue

            instance.cohorts.add(cohort)
