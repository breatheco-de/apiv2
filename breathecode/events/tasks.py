import logging
from breathecode.services.eventbrite import Eventbrite
from celery import shared_task, Task
from .models import Organization, EventbriteWebhook
from .actions import sync_org_events

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_organization_events(self, args):
    logger.debug("Starting persist_organization_events")
    org = Organization.objects.get(id=args['org_id'])
    result = sync_org_events(org)
    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_eventbrite_webhook(self, eventbrite_webhook_id):
    logger.debug("Starting async_eventbrite_webhook")
    status = 'ok'

    webhook = EventbriteWebhook.objects.filter(
        id=eventbrite_webhook_id).first()
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
