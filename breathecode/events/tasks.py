import logging
from breathecode.services.eventbrite import Eventbrite
from celery import shared_task, Task
from .models import Organization, EventbriteWebhook
from .actions import sync_org_events

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_organization_events(self,args):
    org = Organization.objects.get(id=args['org_id'])
    result = sync_org_events(org)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_eventbrite_webhook(self, eventbrite_webhook_id):
    status = 'ok'

    organization_id = (EventbriteWebhook.objects.filter(id=eventbrite_webhook_id)
        .values_list('organization_id', flat=True).first())

    if not organization_id:
        raise Exception("Invalid organization_id")

    organization = Organization.objects.filter(id=organization_id).first()

    if not organization:
        raise Exception("Organization doesn't exist")

    try:
        client = Eventbrite(organization.eventbrite_key)
        client.execute_action(eventbrite_webhook_id)
    except Exception as e:
        logger.debug(f'Eventbrite exception')
        logger.debug(str(e))
        status = 'error'

    logger.debug(f'Eventbrite status: {status}')
 