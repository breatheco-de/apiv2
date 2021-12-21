import logging
from celery import shared_task, Task
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.services.activecampaign import ActiveCampaign
from breathecode.monitoring.actions import test_link
from .models import FormEntry, ShortLink, ActiveCampaignWebhook, ActiveCampaignAcademy, Tag
from .actions import register_new_lead, save_get_geolocal, acp_ids

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 1, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def persist_leads():
    logger.debug('Starting persist_leads')
    entries = FormEntry.objects.filter(storage_status='PENDING')
    for entry in entries:
        form_data = entry.toFormData()
        result = register_new_lead(form_data)
        if result is not None and result != False:
            save_get_geolocal(entry, form_data)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def persist_single_lead(self, form_data):
    logger.debug('Starting persist_single_lead')
    entry = register_new_lead(form_data)
    if entry is not None and entry != False:
        save_get_geolocal(entry, form_data)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def update_link_viewcount(self, slug):
    logger.debug('Starting update_link_viewcount')

    sl = ShortLink.objects.filter(slug=slug).first()
    if sl is None:
        logger.debug(f'ShortLink with slug {slug} not found')
        return False

    sl.hits = sl.hits + 1
    sl.lastclick_at = timezone.now()
    sl.save()

    result = test_link(url=sl.destination)
    if result['status_code'] < 200 or result['status_code'] > 299:
        sl.destination_status_text = result['status_text']
        sl.destination_status = 'ERROR'
        sl.save()
    else:
        sl.destination_status = 'ACTIVE'
        sl.destination_status_text = result['status_text']
        sl.save()


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_activecampaign_webhook(self, webhook_id):
    logger.debug('Starting async_activecampaign_webhook')
    status = 'ok'

    webhook = ActiveCampaignWebhook.objects.filter(id=webhook_id).first()
    ac_academy = webhook.ac_academy

    if ac_academy is not None:
        try:
            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            client.execute_action(webhook_id, acp_ids)
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


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_cohort_task_to_student(self, user_id, cohort_id, academy_id):
    logger.debug('Task process_cohortuser_add started')

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        raise Exception(f'ActiveCampaign Academy {str(academy_id)} not found')

    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise Exception(f'user with id {str(user_id)} not found')

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise Exception(f'Cohort {str(cohort_id)} not found')

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag = Tag.objects.filter(slug=cohort.slug, ac_academy__id=ac_academy.id).first()
    if tag is None:
        logger.debug(
            f'Cohort tag {cohort.slug} does not exist in the system, the tag could not be added to the student. This tag was supposed to be created by the system when creating a new cohort'
        )
        return True

    if tag is not None:
        contact = client.get_contact_by_email(user.email)
        if contact is None:
            logger.debug(f'No contact found on activecampaign, could not add cohort tag to the student')

        logger.debug(f'Adding tag {tag.id} to acp contact {contact["id"]}')
        client.add_tag_to_contact(contact['id'], tag.acp_id)
    else:
        return False


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_cohort_slug_as_acp_tag(self, cohort_id: int, academy_id: int) -> None:
    logger.warn('Task add_cohort_slug_as_acp_tag started')

    if not Academy.objects.filter(id=academy_id).exists():
        logger.error(f'Academy {academy_id} not found')
        return

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        logger.error(f'ActiveCampaign Academy {academy_id} not found')
        return

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        logger.error(f'Cohort {cohort_id} not found')
        return

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag = Tag.objects.filter(slug=cohort.slug, ac_academy__id=ac_academy.id).first()
    if tag:
        logger.warn(f'Tag for cohort `{cohort.slug}` already exists')
        return

    try:
        data = client.create_tag(cohort.slug,
                                 description=f'Cohort {cohort.slug} at {ac_academy.academy.slug}')

        tag = Tag(slug=data['tag'], acp_id=data['id'], tag_type='OTHER', ac_academy=ac_academy, subscribers=0)
        tag.save()

    except:
        pass
