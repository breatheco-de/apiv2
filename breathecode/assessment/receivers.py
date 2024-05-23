import logging
from typing import Any, Type
from breathecode.admissions.signals import syllabus_asset_slug_updated
from .signals import userassessment_status_updated
from .models import UserAssessment
from .tasks import async_close_userassignment
from django.dispatch import receiver
from breathecode.assignments import tasks

logger = logging.getLogger(__name__)


@receiver(userassessment_status_updated, sender=UserAssessment)
def userassessment_status_updated(sender: Type[UserAssessment], instance: UserAssessment, **kwargs: Any):
    logger.info('Processing userassessment_status_updated: ' + str(instance.id))
    if instance.status == 'ANSWERED':
        async_close_userassignment.delay(instance.id)
