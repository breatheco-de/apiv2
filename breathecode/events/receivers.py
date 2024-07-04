import logging
from typing import Any, Type

from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortTimeSlot
from breathecode.admissions.signals import timeslot_saved
from breathecode.events import tasks

logger = logging.getLogger(__name__)


@receiver(timeslot_saved, sender=CohortTimeSlot)
def post_save_cohort_time_slot(sender: Type[CohortTimeSlot], instance: CohortTimeSlot, **kwargs: Any):
    logger.info("Procesing CohortTimeSlot save")

    if (
        instance.cohort.ending_date
        and instance.cohort.ending_date > timezone.now()
        and instance.cohort.never_ends == False
    ):
        tasks.build_live_classes_from_timeslot.delay(instance.id)
