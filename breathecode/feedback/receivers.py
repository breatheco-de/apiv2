import logging
from django.dispatch import receiver
from django.db.models import Avg
from .signals import survey_answered
from breathecode.admissions.signals import student_graduated
from breathecode.admissions.models import CohortUser
from .models import Answer
from .tasks import process_student_graduation, process_answer_received

logger = logging.getLogger(__name__)


@receiver(survey_answered, sender=Answer)
def answer_received(sender, instance, **kwargs):
    """
    Update survey avg score when new answers are received
    also notivy bad nps score.
    """
    logger.debug('Answer received, calling task process_answer_received')
    process_answer_received.delay(instance.id)

@receiver(student_graduated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **kwargs):
    logger.debug('Received student_graduated signal')
    process_student_graduation.delay(instance.cohort.id, instance.user.id)