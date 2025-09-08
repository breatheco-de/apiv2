import logging
from typing import Type

from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import Group

from breathecode.authenticate.models import GoogleWebhook, UserInvite
from breathecode.authenticate.signals import google_webhook_saved, invite_status_updated
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.payments import tasks

from .models import Consumable, Plan, PlanFinancing, Subscription, SubscriptionSeat, SubscriptionSeatInvite
from . import actions as payments_actions
from .signals import (
    consume_service,
    grant_service_permissions,
    lose_service_permissions,
    reimburse_service_units,
    update_plan_m2m_service_items,
    grant_plan_permissions,
    revoke_plan_permissions,
)

logger = logging.getLogger(__name__)


@receiver(consume_service, sender=Consumable)
def consume_service_receiver(sender: Type[Consumable], instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == 0:
        lose_service_permissions.send_robust(instance=instance, sender=sender)
        return

    if instance.how_many == -1:
        return

    instance.how_many -= how_many
    instance.save()

    if instance.how_many == 0:
        lose_service_permissions.send_robust(instance=instance, sender=sender)


@receiver(reimburse_service_units, sender=Consumable)
def reimburse_service_units_receiver(sender: Type[Consumable], instance: Consumable, how_many: float, **kwargs):
    if instance.how_many == -1:
        return

    grant_permissions = not instance.how_many and how_many

    instance.how_many += how_many
    instance.save()

    if grant_permissions:
        grant_service_permissions.send_robust(instance=instance, sender=sender)


@receiver(lose_service_permissions, sender=Consumable)
def lose_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    now = timezone.now()

    if instance.how_many != 0:
        return

    consumables = Consumable.objects.filter(Q(valid_until__lte=now) | Q(valid_until=None), user=instance.user).exclude(
        how_many=0
    )

    # for group in instance.user.groups.all():
    for group in instance.service_item.service.groups.all():
        # if group ==
        how_many = consumables.filter(service_item__service__groups__name=group.name).distinct().count()
        if how_many == 0:
            instance.user.groups.remove(group)


@receiver(grant_service_permissions, sender=Consumable)
def grant_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    groups = instance.service_item.service.groups.all()

    for group in groups:
        if not instance.user.groups.filter(name=group.name).exists():
            instance.user.groups.add(group)


@receiver(grant_plan_permissions, sender=Subscription)
@receiver(grant_plan_permissions, sender=PlanFinancing)
def grant_plan_permissions_receiver(
    sender: Type[Subscription] | Type[PlanFinancing], instance: Subscription | PlanFinancing, **kwargs
):
    """
    Add the user to the Paid Student group when a subscription/plan financing is created
    or when its status changes to ACTIVE. The signal is only emitted for paid plans.
    """
    group = Group.objects.filter(name="Paid Student").first()
    if group and not instance.user.groups.filter(name="Paid Student").exists():
        instance.user.groups.add(group)

    # Propagate group access to seat assignees for this subscription
    if isinstance(instance, Subscription) and group:
        for seat in SubscriptionSeat.objects.filter(subscription=instance).select_related("user"):
            if not seat.user.groups.filter(name="Paid Student").exists():
                seat.user.groups.add(group)


@receiver(revoke_plan_permissions, sender=Subscription)
@receiver(revoke_plan_permissions, sender=PlanFinancing)
def revoke_plan_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Paid Student group only if the user has
    NO other active PAID subscriptions or plan financings.
    """
    group = Group.objects.filter(name="Paid Student").first()
    user = instance.user

    if not group or not user.groups.filter(name="Paid Student").exists():
        return

    from .actions import user_has_active_paid_plans

    if not user_has_active_paid_plans(user):
        user.groups.remove(group)

    # Revoke for seat assignees of this subscription if they have no other paid access
    if isinstance(instance, Subscription) and group:
        for seat in SubscriptionSeat.objects.filter(subscription=instance).select_related("user"):
            seat_user = seat.user
            if not user_has_active_paid_plans(seat_user):
                seat_user.groups.remove(group)


@receiver(invite_status_updated, sender=UserInvite)
def handle_seat_invite_accepted(sender: Type[UserInvite], instance: UserInvite, **kwargs):
    """When a seat invite is accepted and binded to a user, convert it into a SubscriptionSeat."""
    if instance.status != "ACCEPTED" or not instance.user_id:
        return

    for seat_invite in SubscriptionSeatInvite.objects.filter(invite=instance).select_related(
        "subscription", "service_item"
    ):
        # Capacity enforcement at acceptance time
        item = seat_invite.service_item
        subscription = seat_invite.subscription
        if not item.can_add_team_member_for_subscription(subscription, additional=1):
            continue

        seat, _ = SubscriptionSeat.objects.get_or_create(
            subscription=subscription,
            service_item=item,
            user=instance.user,
            defaults={"seats": seat_invite.seats},
        )

        # If subscription is already active and paid, ensure group is granted and consumables are issued now
        if subscription.status == Subscription.Status.ACTIVE and payments_actions.is_subscription_paid(subscription):
            group = Group.objects.filter(name="Paid Student").first()
            if group and not instance.user.groups.filter(name="Paid Student").exists():
                instance.user.groups.add(group)

            # Issue consumables for the new seat assignee
            tasks.renew_subscription_consumables.delay(subscription.id)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_ended(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    if instance.mentee and instance.service and instance.status in ["FAILED", "IGNORED"]:
        tasks.refund_mentoring_session.delay(instance.id)


@receiver(m2m_changed, sender=Plan.service_items.through)
def plan_m2m_wrapper(sender: Type[Plan.service_items.through], instance: Plan, **kwargs):
    if kwargs["action"] != "post_add":
        return

    update_plan_m2m_service_items.send_robust(sender=sender, instance=instance)


@receiver(update_plan_m2m_service_items, sender=Plan.service_items.through)
def plan_m2m_changed(sender: Type[Plan.service_items.through], instance: Plan, **kwargs):
    tasks.update_service_stock_schedulers.delay(instance.id)


@receiver(google_webhook_saved, sender=GoogleWebhook)
def process_google_webhook_on_created(sender: Type[GoogleWebhook], instance: GoogleWebhook, created: bool, **kwargs):
    if created:
        tasks.process_google_webhook.delay(instance.id)
