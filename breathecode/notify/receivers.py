"""
Webhook receivers for BreatheCode API.

Most webhook receivers are now auto-registered based on HOOK_EVENTS_METADATA.
This file contains only:
1. Core Django signal receivers (post_save, post_delete, m2m_changed)
2. Manual receivers with custom logic that can't be auto-generated

See breathecode/notify/utils/hook_events.py for webhook event configuration.
See breathecode/notify/utils/auto_register_hooks.py for auto-registration logic.
"""

import logging
from typing import Type

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.admissions.serializers import CohortUserHookSerializer
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.events.models import Event, EventCheckin
from breathecode.events.serializers import EventJoinSmallSerializer
from breathecode.events.signals import event_rescheduled
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.serializers import SessionHookSerializer
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.notify.models import HookError
from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.payments.serializers import GetPlanFinancingSerializer, GetSubscriptionHookSerializer
from breathecode.payments.signals import planfinancing_created, subscription_created

from .tasks import send_mentorship_starting_notification
from .utils.hook_manager import HookManager

logger = logging.getLogger(__name__)


def get_model_label(instance):
    """Get the model label for an instance."""
    if instance is None:
        return None
    opts = instance._meta.concrete_model._meta
    try:
        return opts.label
    except AttributeError:
        return ".".join([opts.app_label, opts.object_name])


# =============================================================================
# Manual Receivers with Custom Logic
# =============================================================================
# These receivers have custom logic beyond standard webhook delivery
# and cannot be auto-registered. They are marked with auto_register=False
# in HOOK_EVENTS_METADATA.


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_status(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    """
    Manual receiver for mentorship session status changes.
    Has custom logic: sends notification email when session starts.
    """
    # Custom logic: Send notification when session starts
    if instance.status == "STARTED":
        logger.debug("Mentorship has started, notifying the mentor")
        send_mentorship_starting_notification.delay(instance.id)

    # Standard webhook delivery
    model_label = get_model_label(instance)
    serializer = SessionHookSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "mentorship_session_status",
        payload_override=serializer.data,
        academy_override=instance.mentor.academy,
    )


@receiver(student_edu_status_updated, sender=CohortUser)
def edu_status_updated(sender, instance, **kwargs):
    """
    Manual receiver for student educational status updates.
    Has custom logic: gets academy from instance.cohort.academy (not instance.academy).
    """
    logger.debug("Sending student to hook with new edu status")
    # Custom academy logic: CohortUser doesn't have direct academy field
    academy = instance.cohort.academy if instance.cohort is not None else None
    model_label = get_model_label(instance)
    serializer = CohortUserHookSerializer(instance)
    HookManager.process_model_event(
        instance, model_label, "edu_status_updated", payload_override=serializer.data, academy_override=academy
    )


@receiver(event_rescheduled, sender=Event)
def handle_event_rescheduled(sender, instance, **kwargs):
    """
    Manual receiver for event rescheduling.
    Has custom logic: builds bulk email payload with attendee recipients list.
    """
    logger.info("Sending event_rescheduled hook with new starting at")
    model_label = get_model_label(instance)
    serializer = EventJoinSmallSerializer(instance)

    # Custom logic: Build bulk email payload with attendee list
    checkins = EventCheckin.objects.filter(event=instance, attendee__isnull=False, status="PENDING").select_related(
        "attendee"
    )
    if checkins.exists():
        email_list = [checkin.attendee.email for checkin in checkins]
        bulk_email_payload = {"event": serializer.data, "recipients": email_list}
        HookManager.process_model_event(instance, model_label, "event_rescheduled", payload_override=bulk_email_payload)


@receiver(m2m_changed, sender=PlanFinancing.invoices.through)
def planfinancing_invoices_added(sender, instance, action, **kwargs):
    """
    Detects when invoices are added to a PlanFinancing for the first time to call the planfinancing_created signal.
    If plans are already assigned, dispatches planfinancing_created signal. (otherwise it will be dispatched whithout plans or invoices)
    """
    # Only execute after invoices are added
    if action != "post_add":
        return

    invoices_count = instance.invoices.count()
    pk_set = kwargs.get("pk_set", set())

    # Check if this is the first time invoices are being added (was empty before)
    # AND that plans already exist
    if invoices_count == len(pk_set):
        logger.debug(f"Invoices added to new PlanFinancing {instance.id}, dispatching planfinancing_created signal")
        planfinancing_created.send_robust(sender=PlanFinancing, instance=instance)


@receiver(planfinancing_created, sender=PlanFinancing)
def new_planfinancing_created(sender, instance, **kwargs):
    """
    Manual receiver for new PlanFinancing creation.
    Has custom logic: waits to be called after invoices are added to the PlanFinancing to ensure many to many relationships are set.
    """
    logger.debug("Sending new PlanFinancing to hook")
    model_label = get_model_label(instance)
    serializer = GetPlanFinancingSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "planfinancing_created",
        payload_override=serializer.data,
        academy_override=instance.academy,
    )


@receiver(m2m_changed, sender=Subscription.invoices.through)
def subscription_invoices_added(sender, instance, action, **kwargs):
    """
    Detects when invoices are added to a Subscription for the first time to call the subscription_created signal.
    If plans are already assigned, dispatches subscription_created signal. (otherwise it will be dispatched whithout plans or invoices)
    """
    # Only execute after invoices are added
    if action != "post_add":
        return

    invoices_count = instance.invoices.count()
    pk_set = kwargs.get("pk_set", set())

    # Check if this is the first time invoices are being added (was empty before)
    # AND that plans already exist
    if invoices_count == len(pk_set):
        logger.debug(f"Invoices added to new Subscription {instance.id}, dispatching subscription_created signal")
        subscription_created.send_robust(sender=Subscription, instance=instance)


@receiver(subscription_created, sender=Subscription)
def new_subscription_created(sender, instance, **kwargs):
    """
    Manual receiver for new Subscription creation.
    Has custom logic: waits to be called after invoices are added to the Subscription to ensure many to many relationships are set.
    """
    logger.debug("Sending new Subscription to hook")
    model_label = get_model_label(instance)
    serializer = GetSubscriptionHookSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "subscription_created",
        payload_override=serializer.data,
        academy_override=instance.academy,
    )


# =============================================================================
# Core Django Signal Receivers
# =============================================================================
# These handle Django's built-in signals (post_save, post_delete, m2m_changed)
# and are required for the REST Hooks system to work.


@receiver(post_save, dispatch_uid="instance-saved-hook")
def model_saved(sender, instance, created, raw, using, **kwargs):
    """
    Automatically triggers "created" and "updated" webhook actions for all models.
    This is part of the Django REST Hooks system.
    """
    model_label = get_model_label(instance)
    action = "created" if created else "updated"
    HookManager.process_model_event(instance, model_label, action)


@receiver(post_delete, dispatch_uid="instance-deleted-hook")
def model_deleted(sender, instance, using, **kwargs):
    """
    Automatically triggers "deleted" webhook actions for all models.
    This is part of the Django REST Hooks system.
    """
    model_label = get_model_label(instance)
    HookManager.process_model_event(instance, model_label, "deleted")


@receiver(m2m_changed, sender=HookError.hooks.through)
def update_updated_at(sender, instance, **kwargs):
    """Update the updated_at field when hooks are added to HookError."""
    instance.updated_at = timezone.now()
    instance.save()
