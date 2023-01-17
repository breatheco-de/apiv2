import logging
from typing import Any, Type
from django.dispatch import receiver
from breathecode.admissions.models import CohortTimeSlot
from breathecode.events.signals import event_saved
from breathecode.events.models import Event
from .tasks import async_export_event_to_eventbrite
from django.db.models.signals import post_save
from breathecode.events import tasks

logger = logging.getLogger(__name__)


@receiver(event_saved, sender=Event)
def post_save_event(sender: Type[CohortTimeSlot], instance: Event, **kwargs: Any):
    logger.debug('Procesing event save')
    if instance.sync_with_eventbrite and instance.eventbrite_sync_status == 'PENDING':
        async_export_event_to_eventbrite.delay(instance.id)


@receiver(post_save, sender=CohortTimeSlot)
def post_save_cohort_time_slot(sender: Type[CohortTimeSlot], instance: CohortTimeSlot, **kwargs: Any):
    logger.info('Procesing CohortTimeSlot save')
    tasks.build_live_classes_from_timeslot.delay(instance.id)
