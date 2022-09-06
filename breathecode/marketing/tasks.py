from typing import Optional
from celery import shared_task, Task
from django.utils import timezone
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event
from breathecode.services.activecampaign import ActiveCampaign
from breathecode.monitoring.actions import test_link
from breathecode.utils import getLogger
from .models import FormEntry, ShortLink, ActiveCampaignWebhook, ActiveCampaignAcademy, Tag, Downloadable
from .actions import register_new_lead, save_get_geolocal, acp_ids

logger = getLogger(__name__)


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
        message = f"ActiveCampaign Academy Profile {webhook_id} doesn\'t exist"

        webhook.status = 'ERROR'
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = 'error'

    logger.debug(f'ActiveCampaign webook status: {status}')


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_cohort_task_to_student(self, user_id, cohort_id, academy_id):
    logger.warn('Task add_cohort_task_to_student started')

    if not Academy.objects.filter(id=academy_id).exists():
        logger.error(f'Academy {academy_id} not found')
        return

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        logger.error(f'ActiveCampaign Academy {academy_id} not found')
        return

    user = User.objects.filter(id=user_id).first()
    if user is None:
        logger.error(f'User {user_id} not found')
        return

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        logger.error(f'Cohort {cohort_id} not found')
        return

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag = Tag.objects.filter(slug__iexact=cohort.slug, ac_academy__id=ac_academy.id).first()

    if tag is None:
        logger.error(
            f'Cohort tag `{cohort.slug}` does not exist in the system, the tag could not be added to the student. '
            'This tag was supposed to be created by the system when creating a new cohort')
        return False

    try:
        contact = client.get_contact_by_email(user.email)

        logger.warn(f'Adding tag {tag.id} to acp contact {contact["id"]}')
        client.add_tag_to_contact(contact['id'], tag.acp_id)

    except Exception as e:
        logger.error(str(e))


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_event_tags_to_student(self,
                              event_id: int,
                              user_id: Optional[int] = None,
                              email: Optional[str] = None):
    logger.warn('Task add_event_tags_to_student started')

    if not user_id and not email:
        logger.error('Impossible to determine the user email')
        return

    if user_id and email:
        logger.error('You can\'t provide the user_id and email together')
        return

    if not email:
        email = User.objects.filter(id=user_id).values_list('email', flat=True).first()

    if not email:
        logger.error('We can\'t get the user email')
        return

    event = Event.objects.filter(id=event_id).first()
    if event is None:
        logger.error(f'Event {event_id} not found')
        return

    if not event.academy:
        logger.error(f'Impossible to determine the academy')
        return

    academy = event.academy

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy.id).first()
    if ac_academy is None:
        logger.error(f'ActiveCampaign Academy {academy.id} not found')
        return

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag_slugs = [x for x in event.tags.split(',') if x]  # prevent a tag with the slug ''
    if event.slug:
        tag_slugs.append(f'event-{event.slug}' if not event.slug.startswith('event-') else event.slug)

    tags = Tag.objects.filter(slug__in=tag_slugs, ac_academy__id=ac_academy.id)
    if not tags:
        logger.warn('Tags not found')
        return

    try:
        contact = client.get_contact_by_email(email)
        for tag in tags:
            logger.warn(f'Adding tag {tag.id} to acp contact {contact["id"]}')
            client.add_tag_to_contact(contact['id'], tag.acp_id)

    except Exception as e:
        logger.error(str(e))


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

        tag = Tag(slug=data['tag'],
                  acp_id=data['id'],
                  tag_type='COHORT',
                  ac_academy=ac_academy,
                  subscribers=0)
        tag.save()

    except:
        logger.exception(f'There was an error creating tag for cohort {cohort.slug}',
                         slug='exception-creating-tag-in-acp')


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_event_slug_as_acp_tag(self, event_id: int, academy_id: int, force=False) -> None:
    logger.warn('Task add_event_slug_as_acp_tag started')

    if not Academy.objects.filter(id=academy_id).exists():
        logger.error(f'Academy {academy_id} not found')
        return

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        logger.error(f'ActiveCampaign Academy {academy_id} not found')
        return

    event = Event.objects.filter(id=event_id).first()
    if event is None:
        logger.error(f'Event {event_id} not found')
        return

    if not event.slug:
        logger.error(f'Event {event_id} does not have slug')
        return

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)

    if event.slug.startswith('event-'):
        new_tag_slug = event.slug
    else:
        new_tag_slug = f'event-{event.slug}'

    if (tag := Tag.objects.filter(slug=new_tag_slug, ac_academy__id=ac_academy.id).first()) and not force:
        logger.error(f'Tag for event `{event.slug}` already exists')
        return

    try:
        data = client.create_tag(new_tag_slug, description=f'Event {event.slug} at {ac_academy.academy.slug}')

        # retry create the tag in Active Campaign
        if tag:
            tag.slug = data['tag']
            tag.acp_id = data['id']
            tag.tag_type = 'EVENT'
            tag.ac_academy = ac_academy

        else:
            tag = Tag(slug=data['tag'],
                      acp_id=data['id'],
                      tag_type='EVENT',
                      ac_academy=ac_academy,
                      subscribers=0)

        tag.save()

    except:
        logger.exception(f'There was an error creating tag for event {event.slug}',
                         slug='exception-creating-tag-in-acp')


@shared_task(bind=True, base=BaseTaskWithRetry)
def add_downloadable_slug_as_acp_tag(self, downloadable_id: int, academy_id: int) -> None:
    logger.warn('Task add_downloadable_slug_as_acp_tag started')

    if not Academy.objects.filter(id=academy_id).exists():
        logger.error(f'Academy {academy_id} not found')
        return

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        logger.error(f'ActiveCampaign Academy {academy_id} not found')
        return

    downloadable = Downloadable.objects.filter(id=downloadable_id).first()
    if downloadable is None:
        logger.error(f'Downloadable {downloadable_id} not found')
        return

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)

    if downloadable.slug.startswith('down-'):
        new_tag_slug = downloadable.slug
    else:
        new_tag_slug = f'down-{downloadable.slug}'

    tag = Tag.objects.filter(slug=new_tag_slug, ac_academy__id=ac_academy.id).first()

    if tag:
        logger.warn(f'Tag for downloadable `{downloadable.slug}` already exists')
        return

    try:
        data = client.create_tag(new_tag_slug,
                                 description=f'Downloadable {downloadable.slug} at {ac_academy.academy.slug}')

        tag = Tag(slug=data['tag'],
                  acp_id=data['id'],
                  tag_type='DOWNLOADABLE',
                  ac_academy=ac_academy,
                  subscribers=0)
        tag.save()

    except:
        logger.exception(f'There was an error creating tag for downloadable {downloadable.slug}')


@shared_task(bind=True, base=BaseTaskWithRetry)
def create_form_entry(self, item, csv_upload_id):
    form_entry = FormEntry()
    csv_upload.log = ''
    if 'first_name' in item:
        form_entry.first_name = item['first_name']
    if 'last_name' in item:
        form_entry.last_name = item['last_name']
    if 'email' in item:
        form_entry.email = item['email']
    if 'location' in item:
        form_entry.location = item['location']
    if 'academy' in item:
        form_entry.academy = item['academy']

    form_entry.save()

    # if not form_entry.first_name or not form_entry.last_name or not form_entry.email or not form_entry.location or not form_entry.academy:

    csv_upload = CSVUpload()

    if not form_entry.first_name:
        csv_upload.log += 'No first name in form entry, '

    if not form_entry.last_name:
        csv_upload.log += 'No last name in form entry, '

    if not form_entry.email:
        csv_upload.log += 'No email in form entry, '

    if not form_entry.location or not form_entry.academy:
        csv_upload.log += 'No location or academy in form entry, '

    if csv_upload.log.endswith(', '):
        csv_upload.log = csv_upload.log[0:-2]
