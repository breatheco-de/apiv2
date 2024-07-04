import logging
from typing import Type

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.serializers import CohortHookSerializer, CohortUserHookSerializer
from breathecode.admissions.signals import cohort_stage_updated, student_edu_status_updated
from breathecode.authenticate.models import UserInvite
from breathecode.authenticate.signals import invite_status_updated
from breathecode.events.models import Event, EventCheckin
from breathecode.events.serializers import EventHookCheckinSerializer, EventJoinSmallSerializer
from breathecode.events.signals import event_status_updated, new_event_attendee, new_event_order
from breathecode.marketing.models import FormEntry
from breathecode.marketing.serializers import FormEntryHookSerializer
from breathecode.marketing.signals import form_entry_won_or_lost, new_form_entry_deal
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.serializers import SessionHookSerializer
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.notify.models import HookError
from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.payments.serializers import GetPlanFinancingSerializer, GetSubscriptionHookSerializer
from breathecode.payments.signals import planfinancing_created, subscription_created
from breathecode.registry.models import Asset
from breathecode.registry.serializers import AssetHookSerializer
from breathecode.registry.signals import asset_status_updated

from .tasks import send_mentorship_starting_notification
from .utils.hook_manager import HookManager

logger = logging.getLogger(__name__)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_status(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    if instance.status == "STARTED":
        logger.debug("Mentorship has started, notifying the mentor")
        send_mentorship_starting_notification.delay(instance.id)

    model_label = get_model_label(instance)
    serializer = SessionHookSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "mentorship_session_status",
        payload_override=serializer.data,
        academy_override=instance.mentor.academy,
    )


def get_model_label(instance):
    if instance is None:
        return None
    opts = instance._meta.concrete_model._meta
    try:
        return opts.label
    except AttributeError:
        return ".".join([opts.app_label, opts.object_name])


# Django Rest Hooks Receivers


@receiver(post_save, dispatch_uid="instance-saved-hook")
def model_saved(sender, instance, created, raw, using, **kwargs):
    """
    Automatically triggers "created" and "updated" actions.
    """
    model_label = get_model_label(instance)
    action = "created" if created else "updated"
    HookManager.process_model_event(instance, model_label, action)


@receiver(post_delete, dispatch_uid="instance-deleted-hook")
def model_deleted(sender, instance, using, **kwargs):
    """
    Automatically triggers "deleted" actions.
    """
    model_label = get_model_label(instance)
    HookManager.process_model_event(instance, model_label, "deleted")


@receiver(form_entry_won_or_lost, sender=FormEntry)
def form_entry_updated(sender, instance, **kwargs):
    logger.debug("Sending formentry to hook")
    model_label = get_model_label(instance)

    serializer = FormEntryHookSerializer(instance)
    HookManager.process_model_event(instance, model_label, "won_or_lost", payload_override=serializer.data)


@receiver(cohort_stage_updated, sender=Cohort)
def new_cohort_stage_updated(sender, instance, **kwargs):

    model_label = get_model_label(instance)

    serializer = CohortHookSerializer(instance)
    HookManager.process_model_event(instance, model_label, "cohort_stage_updated", payload_override=serializer.data)


@receiver(new_form_entry_deal, sender=FormEntry)
def new_form_entry_deal(sender, instance, **kwargs):
    logger.debug("Sending formentry with new deal to hook")
    model_label = get_model_label(instance)

    serializer = FormEntryHookSerializer(instance)
    HookManager.process_model_event(instance, model_label, "new_deal", payload_override=serializer.data)


@receiver(new_event_attendee, sender=EventCheckin)
def handle_new_event_attendee(sender, instance, **kwargs):
    logger.debug("Sending new event attendance")
    model_label = get_model_label(instance)
    serializer = EventHookCheckinSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "new_event_attendee",
        payload_override=serializer.data,
        academy_override=instance.event.academy,
    )


@receiver(new_event_order, sender=EventCheckin)
def handle_new_event_order(sender, instance, **kwargs):
    logger.debug("Sending new event order")
    model_label = get_model_label(instance)
    serializer = EventHookCheckinSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "new_event_order",
        payload_override=serializer.data,
        academy_override=instance.event.academy,
    )


@receiver(event_status_updated, sender=Event)
def handle_event_status_updated(sender, instance, **kwargs):
    # logger.debug('Sending event_status_updated hook with new event status')
    model_label = get_model_label(instance)
    serializer = EventJoinSmallSerializer(instance)
    HookManager.process_model_event(instance, model_label, "event_status_updated", payload_override=serializer.data)


@receiver(asset_status_updated, sender=Asset)
def handle_asset_status_updated(sender, instance, **kwargs):
    logger.debug("Sending asset to hook with new status")
    model_label = get_model_label(instance)
    serializer = AssetHookSerializer(instance)
    HookManager.process_model_event(instance, model_label, "asset_status_updated", payload_override=serializer.data)


@receiver(invite_status_updated, sender=UserInvite)
def handle_invite_accepted(sender, instance, **kwargs):
    model_label = get_model_label(instance)
    HookManager.process_model_event(instance, model_label, "invite_status_updated")


@receiver(student_edu_status_updated, sender=CohortUser)
def edu_status_updated(sender, instance, **kwargs):
    logger.debug("Sending student to hook with new edu status")
    academy = instance.cohort.academy if instance.cohort is not None else None
    model_label = get_model_label(instance)
    serializer = CohortUserHookSerializer(instance)
    HookManager.process_model_event(
        instance, model_label, "edu_status_updated", payload_override=serializer.data, academy_override=academy
    )


@receiver(planfinancing_created, sender=PlanFinancing)
def new_planfinancing_created(sender, instance, **kwargs):
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


@receiver(subscription_created, sender=Subscription)
def new_subscription_created(sender, instance, **kwargs):
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


@receiver(m2m_changed, sender=HookError.hooks.through)
def update_updated_at(sender, instance, **kwargs):
    instance.updated_at = timezone.now()
    instance.save()
