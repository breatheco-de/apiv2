import logging
from datetime import timedelta
from typing import Type

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.events.models import Event, LiveClass
from breathecode.events.signals import event_status_updated, liveclass_ended
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_saved

from .models import AcademyFeedbackSettings, Answer, SurveyConfiguration, SurveyResponse, SurveyStudy
from .signals import survey_answered, survey_response_answered
from .tasks import (
    process_answer_received,
    process_student_graduation,
    send_event_survey,
    send_liveclass_survey,
    send_mentorship_session_survey,
)

logger = logging.getLogger(__name__)


@receiver(survey_answered, sender=Answer)
def answer_received(sender, instance, **kwargs):
    """
    Update survey avg score when new answers are received
    also notify bad nps score.
    """
    logger.debug("Answer received, calling task process_answer_received")
    process_answer_received.delay(instance.id)


@receiver(student_edu_status_updated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **kwargs):
    if instance.educational_status == "GRADUATED":
        logger.debug("Procesing student graduation")
        process_student_graduation.delay(instance.cohort.id, instance.user.id)


@receiver(mentorship_session_saved, sender=MentorshipSession)
def post_mentorin_session_ended(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    if instance.status == "COMPLETED" and Answer.objects.filter(mentorship_session__id=instance.id).exists() is False:
        duration = timedelta(seconds=0)
        if instance.started_at is not None and instance.ended_at is not None:
            duration = instance.ended_at - instance.started_at

        if duration > timedelta(minutes=5) and instance.mentor and instance.mentee:
            logger.debug(f"Session lasted for {str(duration.seconds/60)} minutes, sending survey")
            send_mentorship_session_survey.delay(instance.id)


@receiver(liveclass_ended, sender=LiveClass)
def post_liveclass_ended(sender: Type[LiveClass], instance: LiveClass, **kwargs):

    if instance.ended_at is not None and (timezone.now() - instance.ended_at) > timedelta(hours=24):
        logger.debug("LiveClass ended more than 24 hours ago, not sending survey")
        return

    # Check if academy has liveclass survey template configured
    if instance.cohort_time_slot and instance.cohort_time_slot.cohort:
        academy = instance.cohort_time_slot.cohort.academy
        settings = AcademyFeedbackSettings.objects.filter(academy=academy).first()

        if settings and settings.liveclass_survey_template:
            logger.debug(f"Sending survey about live class {instance.id}")
            send_liveclass_survey.delay(instance.id)
        else:
            logger.debug(f"No liveclass survey template configured for academy {academy.name}, skipping survey")


@receiver(event_status_updated, sender=Event)
def post_event_ended(sender: Type[Event], instance: Event, **kwargs):
    if instance.status == "FINISHED" and Answer.objects.filter(event__id=instance.id).exists() is False:
        if instance.ended_at is not None:

            settings = AcademyFeedbackSettings.objects.filter(academy=instance.academy).first()
            if settings and settings.event_survey_template:
                logger.debug("Sending survey for event")
                send_event_survey.delay(instance.id)
            else:
                logger.debug(
                    f"No event survey template configured for academy {instance.academy.name}, skipping survey"
                )


@receiver(survey_response_answered, sender=SurveyResponse)
def post_survey_response_answered(sender: Type[SurveyResponse], instance: SurveyResponse, **kwargs):
    """
    Trigger webhook when a survey response is answered.
    This receiver is called after answers are saved to database.
    """
    from breathecode.notify.utils.hook_manager import HookManager

    try:
        logger.info(f"Survey response {instance.id} answered, triggering webhook")
        academy_override = None
        if getattr(instance, "survey_config", None) and getattr(instance.survey_config, "academy", None):
            academy_override = instance.survey_config.academy

        from breathecode.feedback.serializers import SurveyResponseHookSerializer

        def payload_override(hook, _instance):
            return {"hook": hook.dict(), "data": SurveyResponseHookSerializer(_instance).data}

        HookManager.find_and_fire_hook(
            "survey.survey_answered",
            instance,
            payload_override=payload_override,
            academy_override=academy_override,
        )
    except Exception as e:
        logger.error(f"Error triggering webhook for survey response {instance.id}: {str(e)}", exc_info=True)


@receiver(m2m_changed, sender=SurveyStudy.survey_configurations.through)
def enforce_survey_study_single_trigger_type(sender, instance: SurveyStudy, action, pk_set, **kwargs):
    """
    Prevent SurveyStudy from containing SurveyConfigurations with different trigger_type values.
    This must hold across API, admin, and scripts.
    """

    if action != "pre_add" or not pk_set:
        return

    existing_trigger_types = set(instance.survey_configurations.values_list("trigger_type", flat=True))
    new_trigger_types = set(SurveyConfiguration.objects.filter(pk__in=pk_set).values_list("trigger_type", flat=True))

    trigger_types = existing_trigger_types | new_trigger_types
    if len(trigger_types) <= 1:
        return

    trigger_types_str = ", ".join(sorted([str(x) for x in trigger_types]))
    raise ValidationError(f"All survey configurations in a study must have the same trigger_type, got: {trigger_types_str}")

