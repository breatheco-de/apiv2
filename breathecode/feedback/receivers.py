import logging
from django.dispatch import receiver
from django.db.models import Avg
from .signals import survey_answered
from .models import Answer

logger = logging.getLogger(__name__)


@receiver(survey_answered, sender=Answer)
def answer_received(sender, instance, **kwargs):
    # if a new ProfileAcademy is created on the authanticate app
    # look for the email on the formentry list and bind it
    logger.debug('Answer received, updating survey avg score')
    if instance.survey is not None:
        instance.survey.avg_score = Answer.objects.filter(survey=instance.survey).aggregate(Avg('score'))
        instance.survey.save()
