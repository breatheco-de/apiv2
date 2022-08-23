import logging
from django.dispatch import receiver
from django.db.models import Avg
from datetime import timedelta
from .signals import survey_answered
from breathecode.admissions.signals import student_edu_status_updated
from breathecode.mentorship.signals import mentorship_session_status
from breathecode.admissions.models import CohortUser
from breathecode.mentorship.models import MentorshipSession
from .models import Answer
from .tasks import process_student_graduation, process_answer_received, send_mentorship_session_survey

logger = logging.getLogger(__name__)


@receiver(survey_answered, sender=Answer)
def answer_received(sender, instance, **kwargs):
    """
    Update survey avg score when new answers are received
    also notify bad nps score.
    """
    logger.debug('Answer received, calling task process_answer_received')
    process_answer_received.delay(instance.id)


@receiver(student_edu_status_updated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **kwargs):
    if instance.educational_status == 'GRADUATED':
        logger.debug('Procesing student graduation')
        process_student_graduation.delay(instance.cohort.id, instance.user.id)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentorin_session_ended(sender, instance, **kwargs):
    if instance.status == 'COMPLETED':
        duration = timedelta(seconds=0)
        if instance.started_at is not None and instance.ended_at is not None:
            duration = instance.ended_at - instance.started_at

        if duration > timedelta(minutes=5) and instance.mentor and instance.mentee:
            logger.debug(f'Session lasted for {str(duration.seconds/60)} minutes, sending survey')
            send_mentorship_session_survey.delay(instance.id)
