import logging
from celery import shared_task, Task
from django.db.models import F
from breathecode.services.activecampaign import ActiveCampaign
from .models import FormEntry, ShortLink, ActiveCampaignWebhook
from .actions import register_new_lead, save_get_geolocal

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def persist_leads():
    logger.debug("Starting persist_leads")
    entries = FormEntry.objects.filter(storage_status='PENDING')
    for entry in entries:
        form_data = entry.toFormData()
        result = register_new_lead(form_data)
        if result is not None and result != False:
            save_get_geolocal(entry, form_data)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_single_lead(self, form_data):
    logger.debug("Starting persist_single_lead")
    entry = register_new_lead(form_data)
    if entry is not None and entry != False:
        save_get_geolocal(entry, form_data)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def update_link_viewcount(self, slug):
    logger.debug("Starting update_link_viewcount")
    ShortLink.objects.filter(slug=slug).update(hits=F('hits') + 1)


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_activecampaign_webhook(self, webhook_id):
    logger.debug("Starting async_activecampaign_webhook")
    status = 'ok'

    webhook = ActiveCampaignWebhook.objects.filter(id=webhook_id).first()
    ac_academy = webhook.ac_academy

    if ac_academy is not None:
        try:
            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            client.execute_action(webhook_id)
        except Exception as e:
            logger.debug(f'ActiveCampaign Webhook Exception')
            logger.debug(str(e))
            status = 'error'

    else:
        message = f"ActiveCampaign Academy Profile {organization_id} doesn\'t exist"

        webhook.status = 'ERROR'
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = 'error'

    logger.debug(f'ActiveCampaign webook status: {status}')
