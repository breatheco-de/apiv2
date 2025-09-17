import logging
from typing import Type

from django.contrib.auth.models import Group
from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from task_manager.django.actions import schedule_task

import breathecode.authenticate.tasks as auth_tasks
from breathecode.authenticate.actions import revoke_user_discord_permissions
from breathecode.authenticate.models import Cohort, CredentialsDiscord, GoogleWebhook
from breathecode.authenticate.signals import google_webhook_saved
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.payments import tasks

from .models import Consumable, Plan, PlanFinancing, Subscription
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


@receiver(revoke_plan_permissions, sender=Subscription)
@receiver(revoke_plan_permissions, sender=PlanFinancing)
def revoke_discord_permissions_receiver(sender, instance, **kwargs):
    """
    Remove the user from the Discord server only if the user has
    NO other active 4Geeks Plus PAID subscriptions or plan financings.
    """

    def schedule_delayed_revoke(date_field, date_value):
        if date_value and date_value >= timezone.now():
            minutes_until = int((date_value - timezone.now()).total_seconds() / 60) + 1
            entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"

            unique_task_id = instance.id * 100 + (1 if date_field == "valid_until" else 2)

            manager = schedule_task(auth_tasks.delayed_revoke_discord_permissions, f"{minutes_until}m")
            if not manager.exists(unique_task_id):
                entity_type = "subscription" if isinstance(instance, Subscription) else "plan_financing"
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
    logger.debug(f"plan_slug: {plan_slug}")
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
                    logger.debug("llega el reveivere aqui")

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
        return
    cohort_academy = Cohort.objects.filter(academy=instance.academy).prefetch_related("academy").first()
    cohorts = Cohort.objects.filter(cohortuser__user=instance.user, academy=cohort_academy.academy.id).all()

    plan_slug = Plan.objects.filter(subscription=instance).first().slug
    if plan_slug == "4geeks-plus-subscription" or plan_slug == "4geeks-plus-planfinancing":
        for cohort in cohorts:
            if cohort.shortcuts != None:
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
                        logger.error(f"Error assigning Discord role: {e}")


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
