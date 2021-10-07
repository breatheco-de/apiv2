import logging
from django.dispatch import receiver
from django.db.models import Avg
from .signals import survey_answered
from breathecode.admissions.signals import student_graduated
from breathecode.admissions.models import CohortUser
from .models import Answer
from .tasks import process_student_graduation

logger = logging.getLogger(__name__)


@receiver(survey_answered, sender=Answer)
def answer_received(sender, instance, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    # look for the email on the formentry list and bind it
    logger.debug('Answer received, updating survey avg score')
    if instance.survey is not None:
        survey_score = Answer.objects.filter(survey=instance.survey).aggregate(Avg('score'))
        instance.survey.avg_score = survey_score['score__avg']
        instance.survey.save()

@receiver(student_graduated, sender=CohortUser)
def post_save_cohort_user(sender, instance, **kwargs):
    logger.debug('Received student_graduated signal')
    process_student_graduation.delay(instance.cohort.id, instance.user.id)