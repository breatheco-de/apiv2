import logging
from datetime import timedelta
from typing import Type

from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortUser
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.events.models import Event, LiveClass
from breathecode.events.signals import event_status_updated, liveclass_ended
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_saved

from .models import Answer, AcademyFeedbackSettings
from .signals import survey_answered
from .tasks import (
    process_answer_received,
    process_student_graduation,
    send_event_survey,
    send_mentorship_session_survey,
    send_liveclass_survey,
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
            logger.debug("Sending survey for event")
            send_event_survey.delay(instance.id)
