import logging
from breathecode.services.eventbrite import Eventbrite
from celery import shared_task, Task
from .models import Event, Organization, EventbriteWebhook

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_organization_events(self, args):
    from .actions import sync_org_events

    logger.debug('Starting persist_organization_events')
    org = Organization.objects.get(id=args['org_id'])
    result = sync_org_events(org)
    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_eventbrite_webhook(self, eventbrite_webhook_id):
    logger.debug('Starting async_eventbrite_webhook')
    status = 'ok'

    webhook = EventbriteWebhook.objects.filter(id=eventbrite_webhook_id).first()
    organization_id = webhook.organization_id
    organization = Organization.objects.filter(id=organization_id).first()

    if organization:
        try:
            client = Eventbrite(organization.eventbrite_key)
            client.execute_action(eventbrite_webhook_id)
        except Exception as e:
            logger.debug(f'Eventbrite exception')
            logger.debug(str(e))
            status = 'error'

    else:
        message = f"Organization {organization_id} doesn\'t exist"

        webhook.status = 'ERROR'
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = 'error'

    logger.debug(f'Eventbrite status: {status}')


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_export_event_to_eventbrite(self, event_id: int):
    from .actions import export_event_to_eventbrite

    logger.debug('Starting async_eventbrite_webhook')

    event = Event.objects.filter(id=event_id).first()
    if not event:
        logger.error(f'Event {event_id} not fount')
        return

    if not event.organization:
        logger.error(f'Event {event_id} not have a organization assigned')
        return

    try:
        export_event_to_eventbrite(event, event.organization)
    except Exception as e:
        logger.exception(f'The {event_id} export was failed')
