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

from .models import (
    Consumable,
    Plan,
    PlanFinancing,
    Subscription,
    SubscriptionSeat,
    SubscriptionBillingTeam,
)
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

    user = instance.subscription_seat.user if instance.subscription_seat else instance.user
    subscription_team = instance.subscription_billing_team or (
        instance.subscription_seat.billing_team if instance.subscription_seat else None
    )

    # Build base filter: user and seat consumables
    if subscription_team:
        # limit to consumables linked to the same billing team
        base_filter = Q(user=user, subscription_billing_team=subscription_team) | Q(
            subscription_seat__user=user, subscription_seat__billing_team=subscription_team
        )
    else:
        base_filter = Q(user=user) | Q(subscription_seat__user=user)

    # Include team-shared consumables only if strategy is PER_TEAM
    team_shared_filter = Q()
    if (
        subscription_team
        and subscription_team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM
    ):
        team_shared_filter = Q(
            user__isnull=True,
            subscription_billing_team__isnull=False,
            subscription_billing_team=subscription_team,
        )

    consumables = Consumable.objects.filter(
        Q(valid_until__lte=now) | Q(valid_until=None),
        base_filter | team_shared_filter,
    ).exclude(how_many=0)

    # for group in instance.user.groups.all():
    for group in instance.service_item.service.groups.all():

        how_many = consumables.filter(service_item__service__groups__name=group.name).distinct().count()
        if how_many == 0:
            user.groups.remove(group)


def grant_service_permissions_receiver(sender: Type[Consumable], instance: Consumable, **kwargs):
    # Only grant when this consumable has units available now (> 0). Infinite (-1) is handled elsewhere.
    if instance.how_many <= 0:
        return

    # Determine the affected user and billing team context
    user = instance.subscription_seat.user if instance.subscription_seat else instance.user
    subscription_team = instance.subscription_billing_team or (
        instance.subscription_seat.billing_team if instance.subscription_seat else None
    )

    groups = instance.service_item.service.groups.all()

    def grant_for_user(target_user):
        for group in groups:
            if not target_user.groups.filter(name=group.name).exists():
                target_user.groups.add(group)

    if not user and subscription_team:
        # Grant to all users in the team only if the consumption strategy is PER_TEAM
        if subscription_team.consumption_strategy == SubscriptionBillingTeam.ConsumptionStrategy.PER_TEAM:
            seats = SubscriptionSeat.objects.filter(billing_team=subscription_team, user__isnull=False).select_related(
                "user"
            )
            for seat in seats:
                grant_for_user(seat.user)
        return

    if user:
        grant_for_user(user)


grant_service_permissions.connect(grant_service_permissions_receiver, sender=Consumable)


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


# to be able to use unittest instead of integration test
invite_status_updated.connect(handle_seat_invite_accepted, sender=UserInvite)


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
