import logging
from breathecode.admissions.models import CohortTimeSlot
from breathecode.services.eventbrite import Eventbrite
from celery import shared_task, Task

from breathecode.utils.datetime_interger import DatetimeInteger
from .models import Event, LiveClass, Organization, EventbriteWebhook
from dateutil.relativedelta import relativedelta
from django.utils import timezone

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


@shared_task(bind=True, base=BaseTaskWithRetry)
def build_live_classes_from_timeslot(self, timeslot_id, utc_now=None):
    logger.info(f'Starting build_live_classes_from_timeslot with id {timeslot_id}')

    timeslot = CohortTimeSlot.objects.filter(id=timeslot_id).first()
    if not timeslot:
        logger.error(f'Timeslot {timeslot_id} not fount')
        return

    if not utc_now:
        utc_now = timezone.now()

    cohort = timeslot.cohort
    live_classes = LiveClass.objects.filter(cohort_time_slot=timeslot, starting_at__gte=utc_now)

    starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
    ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
    until_date = timeslot.removed_at or cohort.ending_date

    delta = relativedelta(0)

    if timeslot.recurrency_type == 'DAILY':
        delta += relativedelta(days=1)

    if timeslot.recurrency_type == 'WEEKLY':
        delta += relativedelta(weeks=7)

    if timeslot.recurrency_type == 'MONTHLY':
        delta += relativedelta(months=1)

    if not delta:
        logger.error(f'{timeslot.recurrency_type} is not a valid or not implemented recurrency_type')
        return

    while True:
        schedule, created = LiveClass.objects.get_or_create(
            starting_at=starting_at,
            ending_at=ending_at,
            cohort=cohort,
            defaults={'remote_meeting_url': cohort.online_meeting_url})

        if not created:
            live_classes = live_classes.exclude(id=schedule.id)

        starting_at += delta
        ending_at += delta

        if ending_at > until_date:
            break

    live_classes.delete()
