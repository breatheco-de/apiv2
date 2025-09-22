import logging
from typing import Type

from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from breathecode.authenticate.models import GoogleWebhook, UserInvite
from breathecode.authenticate.signals import google_webhook_saved, invite_status_updated
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.payments import tasks

from .models import (
    Consumable,
    Plan,
    SubscriptionSeat,
    SubscriptionBillingTeam,
)
from .signals import (
    consume_service,
    grant_service_permissions,
    lose_service_permissions,
    reimburse_service_units,
    update_plan_m2m_service_items,
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

    user = instance.subscription_seat.user if instance.subscription_seat else instance.user

    consumables = Consumable.objects.filter(
        Q(valid_until__lte=now) | Q(valid_until=None), Q(user=user) | Q(subscription_seat__user=user)
    ).exclude(how_many=0)

    # for group in instance.user.groups.all():
    for group in instance.service_item.service.groups.all():

        how_many = consumables.filter(service_item__service__groups__name=group.name).distinct().count()
        if how_many == 0:
            user.groups.remove(group)


@receiver(grant_service_permissions, sender=Consumable)
def grant_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    groups = instance.service_item.service.groups.all()
    user = instance.subscription_seat.user if instance.subscription_seat else instance.user

    for group in groups:
        if not user.groups.filter(name=group.name).exists():
            user.groups.add(group)


@receiver(invite_status_updated, sender=UserInvite)
def handle_seat_invite_accepted(sender: Type[UserInvite], instance: UserInvite, **kwargs):
    """When an invite is accepted, bind pending SubscriptionSeat by email and issue consumables."""
    if instance.status != "ACCEPTED" or not instance.user_id:
        return

    # Find pending seats by email across subscriptions with team-enabled items
    seats = SubscriptionSeat.objects.filter(email__iexact=instance.email.strip(), user__isnull=True)
    for seat in seats.select_related("billing_team", "billing_team__subscription"):
        subscription = seat.billing_team.subscription

        # Bind seat to user and normalize email
        seat.user = instance.user
        seat.email = instance.user.email.lower()
        seat.save()

        logger.info(
            "Activated team seat via invite: subscription=%s user=%s",
            subscription.id,
            instance.user_id,
        )

        # Determine effective strategy
        team = seat.billing_team
        plan = subscription.plans.first()
        plan_strategy = getattr(plan, "consumption_strategy", Plan.ConsumptionStrategy.PER_SEAT)
        per_seat_enabled = team and (
            team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_SEAT
            or plan_strategy == Plan.ConsumptionStrategy.BOTH
        )

        # Issue per-seat consumables only when strategy requires it; otherwise rely on renew task for team-level
        if per_seat_enabled:
            tasks.build_service_stock_scheduler_from_subscription.delay(subscription.id, seat_id=seat.id)


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
