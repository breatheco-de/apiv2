import logging
from typing import Any, Type
from django.dispatch import receiver
from breathecode.admissions.models import CohortTimeSlot
from breathecode.events.signals import event_saved
from breathecode.events.models import Event
from .tasks import async_export_event_to_eventbrite
from breathecode.events import tasks
from django.utils import timezone
from breathecode.admissions.signals import timeslot_saved

logger = logging.getLogger(__name__)


@receiver(event_saved, sender=Event)
def post_save_event(sender: Type[Event], instance: Event, **kwargs: Any):
    logger.debug('Procesing event save')
    if instance.sync_with_eventbrite and instance.eventbrite_sync_status == 'PENDING':
        async_export_event_to_eventbrite.delay(instance.id)


@receiver(timeslot_saved, sender=CohortTimeSlot)
def post_save_cohort_time_slot(sender: Type[CohortTimeSlot], instance: CohortTimeSlot, **kwargs: Any):
    logger.info('Procesing CohortTimeSlot save')

    if instance.cohort.ending_date and instance.cohort.ending_date > timezone.now(
    ) and instance.cohort.never_ends == False:
        tasks.build_live_classes_from_timeslot.delay(instance.id)
