import logging
from typing import Type

from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from task_manager.django.actions import schedule_task

import breathecode.authenticate.tasks as auth_tasks
from breathecode.authenticate.actions import revoke_user_discord_permissions
from breathecode.authenticate.models import Cohort, CredentialsDiscord, GoogleWebhook, UserInvite
from breathecode.authenticate.signals import google_webhook_saved, invite_status_updated
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.monitoring import signals as monitoring_signals
from breathecode.monitoring.models import StripeEvent
from breathecode.payments import actions, tasks
from breathecode.payments.models import Invoice

from .actions import validate_auto_recharge_service_units
from .models import (
    Consumable,
    Plan,
    PlanFinancing,
    PlanFinancingSeat,
    PlanFinancingTeam,
    Subscription,
    SubscriptionBillingTeam,
    SubscriptionSeat,
)
from .signals import (
    consume_service,
    grant_plan_permissions,
    grant_service_permissions,
    lose_service_permissions,
    reimburse_service_units,
    revoke_plan_permissions,
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


def grant_plan_permissions_receiver(
    sender: Type[Subscription] | Type[PlanFinancing], instance: Subscription | PlanFinancing, **kwargs
):
    """
    Add the user to the Paid Student group when a subscription/plan financing is created
    or when its status changes to ACTIVE. The signal is only emitted for paid plans.
    """

    def grant(user: User):
        nonlocal group
        if group and not user.groups.filter(name="Paid Student").exists():
            user.groups.add(group)

    group = Group.objects.filter(name="Paid Student").first()
    if isinstance(instance, Subscription) and (
        team := SubscriptionBillingTeam.objects.filter(subscription=instance).first()
    ):
        for seat in team.subscription_seat_set.all():
            grant(seat.user)
    else:
        grant(instance.user)


grant_plan_permissions.connect(grant_plan_permissions_receiver, sender=Subscription)
grant_plan_permissions.connect(grant_plan_permissions_receiver, sender=PlanFinancing)


def revoke_plan_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Paid Student group only if the user has
    NO other active PAID subscriptions or plan financings.
    """

    from .actions import user_has_active_paid_plans

    group = Group.objects.filter(name="Paid Student").first()

    def revoke(user: User):
        nonlocal group
        user = instance.user

        if not group or not user.groups.filter(name="Paid Student").exists():
            return

        if not user_has_active_paid_plans(user):
            user.groups.remove(group)

    if isinstance(instance, Subscription) and (
        team := SubscriptionBillingTeam.objects.filter(subscription=instance).first()
    ):
        for seat in team.subscription_seat_set.all():
            revoke(seat.user)
    else:
        revoke(instance.user)


revoke_plan_permissions.connect(revoke_plan_permissions_receiver, sender=Subscription)
revoke_plan_permissions.connect(revoke_plan_permissions_receiver, sender=PlanFinancing)


def handle_seat_invite_accepted(sender: Type[UserInvite], instance: UserInvite, **kwargs):
    """When an invite is accepted, bind pending SubscriptionSeat by email and issue consumables."""
    if instance.status != "ACCEPTED" or not instance.user_id:
        return

    if instance.plan_financing_seat_id:
        seat = instance.plan_financing_seat
        team = seat.team
        financing = team.financing

        seat.user = instance.user
        seat.email = instance.user.email.lower()
        seat.save(update_fields=["user", "email"])

        logger.info(
            "Activated plan financing seat via invite: financing=%s user=%s",
            financing.id,
            instance.user_id,
        )

        per_team_strategy = team and team.consumption_strategy == PlanFinancingTeam.ConsumptionStrategy.PER_TEAM

        if not per_team_strategy:
            Consumable.objects.filter(plan_financing_seat=seat, user__isnull=True).update(user=instance.user)

        for plan in financing.plans.all():
            actions.grant_student_capabilities(instance.user, plan)

        tasks.build_service_stock_scheduler_from_plan_financing.delay(financing.id, seat_id=seat.id)
        return

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

        # Assign existing consumables that were created with user=None to the newly accepted user
        if per_seat_enabled:
            # Update existing consumables for this seat to assign them to the user
            Consumable.objects.filter(subscription_seat=seat, user__isnull=True).update(user=instance.user)

            # Grant student capabilities for each plan
            for p in subscription.plans.all():
                actions.grant_student_capabilities(instance.user, p)


# to be able to use unittest instead of integration test
invite_status_updated.connect(handle_seat_invite_accepted, sender=UserInvite)


@receiver(revoke_plan_permissions, sender=Subscription)
@receiver(revoke_plan_permissions, sender=PlanFinancing)
def revoke_discord_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Discord server only if the user has
    NO other active 4Geeks Plus PAID subscriptions or plan financings.
    """

    def schedule_delayed_revoke(date_field, date_value):
        if date_value and date_value >= timezone.now():
            days_until = int((date_value - timezone.now()).total_seconds() / (24 * 60 * 60)) + 1
            entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"
            manager = schedule_task(auth_tasks.delayed_revoke_discord_permissions, f"{days_until}d")
            if not manager.exists(instance.id, entity_type, date_field):
                manager.call(instance.id, entity_type, date_field)
            return True
        return False

    from .actions import user_has_active_4geeks_plus_plans

    if user_has_active_4geeks_plus_plans(instance.user):
        logger.info(f"User {instance.user.id} still has active paid plans, skipping Discord permissions revoke")
        return
    entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"
    if entity_type == "subscription":
        plan_slug = Plan.objects.filter(subscription=instance).first().slug
    else:
        plan_slug = Plan.objects.filter(planfinancing=instance).first().slug
    if plan_slug == "4geeks-plus-subscription" or plan_slug == "4geeks-plus-planfinancing":
        if instance.status == "CANCELLED":
            if instance.valid_until:
                if instance.valid_until >= timezone.now():
                    logger.debug(
                        "The user still has time to pay the subscription after being cancelled, scheduling Discord revoke"
                    )
                    schedule_delayed_revoke("valid_until", instance.valid_until)
                    return
                else:
                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return

            if instance.next_payment_at:
                if instance.next_payment_at >= timezone.now():
                    logger.debug(
                        "The user still has time to pay the subscription after being cancelled, scheduling Discord revoke"
                    )
                    schedule_delayed_revoke("next_payment_at", instance.next_payment_at)
                    return
                else:
                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return
        else:

            if instance.valid_until:
                if instance.valid_until >= timezone.now():

                    logger.debug("The user still has time to pay the subscription, scheduling Discord revoke")
                    schedule_delayed_revoke("valid_until", instance.valid_until)
                    return
                else:

                    revoke_user_discord_permissions(instance.user, instance.academy)
                    return
            else:
                revoke_user_discord_permissions(instance.user, instance.academy)
                return


@receiver(grant_plan_permissions, sender=Subscription)
@receiver(grant_plan_permissions, sender=PlanFinancing)
def grant_discord_permissions_receiver(sender, instance, **kwargs):
    discord_creds = CredentialsDiscord.objects.filter(user=instance.user).first()
    if not discord_creds:
        logger.debug(f"User {instance.user.id} has no Discord credentials, skipping grant")
        return False
    cohort_academy = Cohort.objects.filter(academy=instance.academy).prefetch_related("academy").first()
    if not cohort_academy:
        return False
    cohorts = Cohort.objects.filter(cohortuser__user=instance.user, academy=cohort_academy.academy.id).all()

    plan_slug = Plan.objects.filter(subscription=instance).first().slug
    if plan_slug == "4geeks-plus-subscription" or plan_slug == "4geeks-plus-planfinancing":
        for cohort in cohorts:
            if cohort.shortcuts:
                for shortcut in cohort.shortcuts:
                    if shortcut.get("label", None) != "Discord":
                        continue

                    try:
                        auth_tasks.assign_discord_role_task.delay(
                            shortcut.get("server_id", None),
                            int(discord_creds.discord_id),
                            shortcut.get("role_id", None),
                            cohort_academy.academy.id,
                        )
                    except Exception as e:
                        logger.error(str(e))


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_ended(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    if instance.mentee and instance.service and instance.status in ["FAILED", "IGNORED"]:
        tasks.refund_mentoring_session.delay(instance.id)


@receiver(m2m_changed, sender=Plan.service_items.through)
def plan_m2m_wrapper(sender, instance: Plan, **kwargs):
    if kwargs["action"] != "post_add":
        return

    update_plan_m2m_service_items.send_robust(sender=sender, instance=instance)


@receiver(update_plan_m2m_service_items, sender=Plan.service_items.through)
def plan_m2m_changed(sender, instance: Plan, **kwargs):
    tasks.update_service_stock_schedulers.delay(instance.id)


@receiver(google_webhook_saved, sender=GoogleWebhook)
def process_google_webhook_on_created(sender: Type[GoogleWebhook], instance: GoogleWebhook, created: bool, **kwargs):
    if created:
        tasks.process_google_webhook.delay(instance.id)


def check_consumable_balance_for_auto_recharge(sender: Type[Consumable], instance: Consumable, **kwargs):
    """
    Monitor consumable consumption and trigger auto-recharge when balance is low.

    This receiver checks if:
    1. The consumable belongs to a billing team with auto-recharge enabled
    2. The current balance (in subscription currency) falls below the threshold
    3. Monthly spending limit hasn't been exceeded

    If all conditions are met, it triggers a recharge via signal.
    """

    price, amount, error = validate_auto_recharge_service_units(instance)
    if error:
        logger.warning(f"Auto-recharge not allowed for consumable {instance.id}: {error}")
        return

    if amount <= 0:
        logger.warning(f"Auto-recharge not allowed for consumable {instance.id}: amount is zero or negative")
        return

    tasks.process_auto_recharge.delay(instance.id)


post_save.connect(check_consumable_balance_for_auto_recharge, sender=Consumable)
