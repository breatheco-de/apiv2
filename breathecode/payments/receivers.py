import logging

from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from breathecode.notify import actions as notify_actions

from .models import Consumable, ServiceItem, Subscription, Invoice
from .signals import (consume_service, grant_service_permissions, lose_service_permissions,
                      reimburse_service_units, renew_plan, renew_plan_fulfilled, renew_plan_rejected)

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
                                            service=instance.service)  #TODO: check if cant delete the service

    names = []

    for group in instance.groups.all():
        how_many = consumables.filter(service__groups__name=group.name).distinct().count()
        if how_many == 1:
            names.append(group.name)

    # lose the permissions
    instance.user.groups.filter(name_in=names).delete()


@receiver(grant_service_permissions, sender=Consumable)
def grant_service_permissions_receiver(sender, instance: Consumable, **kwargs):
    groups = instance.groups.all()

    for group in groups:
        if not instance.user.groups.filter(name=group.name).exists():
            instance.user.groups.add(group)


@receiver(renew_plan, sender=Subscription)
def renew_plan_receiver(sender, instance: Subscription, **kwargs):
    # put here the code of stripe
    now = timezone.now()

    successfully = True

    service_items = ServiceItem.objects.none()

    for service_item in instance.services:
        if successfully:
            consumable = Consumable(user=instance.user,
                                    service=service_item.service,
                                    unit_type=service_item.unit_type,
                                    how_many=service_item.how_many,
                                    valid_until=None)

            consumable.save()

        service_items |= service_item

    for plan in instance.plans:
        for service_item in plan.services:
            if successfully:
                #TODO: calculate valid_until
                consumable = Consumable(user=instance.user,
                                        service=service_item.service,
                                        unit_type=service_item.unit_type,
                                        how_many=service_item.how_many,
                                        valid_until=...)

                consumable.save()

            service_items |= service_item

    #TODO: calculate valid_until
    invoice = Invoice(amount=instance.amount,
                      user=instance.user,
                      currency=instance.currency,
                      paid_at=now,
                      services=service_items,
                      status='FULFILLED' if successfully else 'REJECTED',
                      valid_until=...)

    invoice.save()

    if successfully:
        renew_plan_fulfilled.send(sender=invoice.__class__, instance=invoice)

    else:
        renew_plan_rejected.send(sender=invoice.__class__, instance=invoice)


@receiver(renew_plan_fulfilled, sender=Invoice)
def renew_plan_fulfilled_receiver(sender, instance: Invoice, **kwargs):
    value = instance.currency.format_value(instance.amount)

    notify_actions.send_email_message(
        'message',
        instance.user.email,
        {
            'SUBJECT': 'Your 4Geeks subscription was successfully renewed',
            'MESSAGE': f'The amount was {value}',
            'BUTTON': f'See the invoice',
            # 'LINK': f'{APP_URL}/invoice/{instance.id}',
        })


@receiver(renew_plan_rejected, sender=Invoice)
def renew_plan_rejected_receiver(sender, instance: Invoice, **kwargs):
    value = instance.currency.format_value(instance.amount)

    notify_actions.send_email_message(
        'message',
        instance.user.email,
        {
            'SUBJECT': 'Your 4Geeks subscription could not be renewed',
            'MESSAGE': f'The amount was {value} but the payment failed',
            'BUTTON': f'See the invoice',
            # 'LINK': f'{APP_URL}/invoice/{instance.id}',
        })
