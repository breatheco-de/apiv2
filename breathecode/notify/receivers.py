import logging
from django.dispatch import receiver
from django.db.models import Avg
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.marketing.signals import form_entry_won_or_lost
from breathecode.marketing.models import FormEntry
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.admissions.models import CohortUser
from breathecode.admissions.serializers import CohortUserHookSerializer
from .tasks import send_mentorship_starting_notification
from .utils.hook_manager import HookManager
from django.db.models.signals import post_save, post_delete

logger = logging.getLogger(__name__)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentorin_session_status(sender, instance, **kwargs):
    if instance.status == 'STARTED':
        logger.debug('Mentorship has started, notifying the mentor')
        send_mentorship_starting_notification.delay(instance.id)


def get_model_label(instance):
    if instance is None:
        return None
    opts = instance._meta.concrete_model._meta
    try:
        return opts.label
    except AttributeError:
        return '.'.join([opts.app_label, opts.object_name])


# Django Rest Hooks Receivers


@receiver(post_save, dispatch_uid='instance-saved-hook')
def model_saved(sender, instance, created, raw, using, **kwargs):
    """
    Automatically triggers "created" and "updated" actions.
    """
    model_label = get_model_label(instance)
    action = 'created' if created else 'updated'
    HookManager.process_model_event(instance, model_label, action)


@receiver(post_delete, dispatch_uid='instance-deleted-hook')
def model_deleted(sender, instance, using, **kwargs):
    """
    Automatically triggers "deleted" actions.
    """
    model_label = get_model_label(instance)
    HookManager.process_model_event(instance, model_label, 'deleted')


@receiver(form_entry_won_or_lost, sender=FormEntry)
def form_entry_updated(sender, instance, **kwargs):
    model_label = get_model_label(instance)
    HookManager.process_model_event(instance, model_label, 'won_or_lost')


@receiver(student_edu_status_updated, sender=CohortUser)
def edu_status_updated(sender, instance, **kwargs):
    logger.debug('Sending student to hook with new edu status')
    model_label = get_model_label(instance)
    serializer = CohortUserHookSerializer(instance)
    HookManager.process_model_event(instance,
                                    model_label,
                                    'edu_status_updated',
                                    payload_override=serializer.data)
