import logging
from breathecode.services.calendly import Calendly
from celery import shared_task

from breathecode.utils.decorators.task import TaskPriority

from .models import CalendlyOrganization, CalendlyWebhook

logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def async_calendly_webhook(self, calendly_webhook_id):
    logger.debug('Starting async_calendly_webhook')
    status = 'ok'

    webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()
    organization = webhook.organization
    if organization is None:
        organization = CalendlyOrganization.objects.filter(hash=webhook.organization_hash).first()

    if organization:
        try:
            client = Calendly(organization.access_token)
            client.execute_action(calendly_webhook_id)
        except Exception as e:
            logger.debug('Calendly webhook exception')
            logger.debug(str(e))
            status = 'error'

    else:
        message = f"Calendly Organization {organization.id} doesn\'t exist"

        webhook.status = 'ERROR'
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = 'error'

    logger.debug(f'Calendly status: {status}')
