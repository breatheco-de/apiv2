import logging
from django.dispatch import receiver
from breathecode.events.signals import sync_with_eventbrite
from breathecode.events.actions import export_event_to_eventbrite
from breathecode.events.models import Event
from .tasks import async_export_event_to_eventbrite
from django.db.models.signals import post_save

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=Event)
@receiver(sync_with_eventbrite, sender=Event)
def post_save_event(sender, instance: Event, **kwargs):
    if instance.sync_with_eventbrite == False or instance.eventbrite_sync_status != 'PENDING':
        logger.debug(f'Skipping post_save_event for {instance}')
        return

    logger.debug('Procesing student graduation')
    async_export_event_to_eventbrite.delay(instance.id)
