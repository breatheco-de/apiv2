# from django.db.models.signals import post_save
from typing import Any, Type
from django.dispatch import receiver

from breathecode.admissions.models import Cohort
from .signals import cohort_log_saved
from ..activity import tasks as activity_tasks
import logging

# add your receives here
logger = logging.getLogger(__name__)


@receiver(cohort_log_saved, sender=Cohort)
def process_cohort_history_log(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info('Procesing Cohort history log for cohort: ' + str(instance.id))

    activity_tasks.get_attendancy_log.delay(instance.id)
