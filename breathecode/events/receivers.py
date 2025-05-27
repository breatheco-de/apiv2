import logging
from typing import Any, Type

from django.dispatch import receiver
from django.utils import timezone

from breathecode.admissions.models import CohortTimeSlot
from breathecode.admissions.signals import timeslot_saved
from breathecode.events import tasks
from breathecode.events.models import Event, FINISHED
from breathecode.events.signals import event_status_updated


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


@receiver(event_status_updated)
def generate_event_recap_on_finished(sender: Type[Event], instance: Event, **kwargs: Any):
    """
    Listen for event status updates and generate a recap when an event is marked as FINISHED.
    """
    logger.info(f"Processing event status update for event {instance.id}")

    # Check if the event status is FINISHED
    if instance.status == FINISHED:
        logger.info(f"Event {instance.id} marked as FINISHED, queuing recap generation")
        tasks.generate_event_recap.delay(instance.id)
