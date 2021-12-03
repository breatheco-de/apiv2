import logging
from django.dispatch import receiver
from breathecode.events.signals import event_saved
from breathecode.events.models import Event
from .tasks import async_export_event_to_eventbrite

logger = logging.getLogger(__name__)


@receiver(event_saved, sender=Event)
def post_save_event(sender, instance: Event, **kwargs):
    logger.debug('Procesing event save')
    if instance.sync_with_eventbrite and instance.eventbrite_sync_status == 'PENDING':
        async_export_event_to_eventbrite.delay(instance.id)
