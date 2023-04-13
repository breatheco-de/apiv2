import logging
from breathecode.admissions.models import CohortTimeSlot
from breathecode.events.actions import fix_datetime_weekday
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
def build_live_classes_from_timeslot(self, timeslot_id: int):
    logger.info(f'Starting build_live_classes_from_timeslot with id {timeslot_id}')

    timeslot = CohortTimeSlot.objects.filter(id=timeslot_id).first()
    if not timeslot:
        logger.error(f'Timeslot {timeslot_id} not fount')
        return

    utc_now = timezone.now()

    cohort = timeslot.cohort
    live_classes = LiveClass.objects.filter(cohort_time_slot=timeslot, starting_at__gte=utc_now)

    starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
    ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
    until_date = timeslot.removed_at or cohort.ending_date
    start_date = cohort.kickoff_date

    # this event end in the new day
    if starting_at > ending_at:
        ending_at.year = starting_at.year
        ending_at.month = starting_at.month
        ending_at.day = starting_at.day + 1

    if not until_date:
        logger.error(f'Timeslot {timeslot_id} not have a ending date')
        live_classes.delete()

        return

    delta = relativedelta(0)

    if timeslot.recurrency_type == 'DAILY':
        delta += relativedelta(days=1)

    if timeslot.recurrency_type == 'WEEKLY':
        delta += relativedelta(weeks=1)

    if timeslot.recurrency_type == 'MONTHLY':
        delta += relativedelta(months=1)

    if not delta:
        logger.error(f'{timeslot.recurrency_type} is not a valid or not implemented recurrency_type')
        return

    while True:

        if ending_at > until_date:
            break

        if starting_at > start_date:
            schedule, _ = LiveClass.objects.get_or_create(
                starting_at=starting_at,
                ending_at=ending_at,
                cohort_time_slot=timeslot,
                defaults={'remote_meeting_url': cohort.online_meeting_url or ''})

            live_classes = live_classes.exclude(id=schedule.id)

            if not timeslot.recurrent:
                break

        starting_at += delta
        ending_at += delta

    live_classes.delete()


@shared_task(bind=True, base=BaseTaskWithRetry)
def fix_live_classes_from_timeslot(self, timeslot_id: int):
    logger.info(f'Starting fix_live_classes_from_timeslot with id {timeslot_id}')

    timeslot = CohortTimeSlot.objects.filter(id=timeslot_id).first()
    if not timeslot:
        logger.error(f'Timeslot {timeslot_id} not fount')
        return

    utc_now = timezone.now()

    cohort = timeslot.cohort
    # live_classes = LiveClass.objects.filter(cohort_time_slot=timeslot, starting_at__gte=utc_now)

    starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
    ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
    until_date = timeslot.removed_at or cohort.ending_date
    start_date = cohort.kickoff_date

    # this event end in the new day
    if starting_at > ending_at:
        ending_at.year = starting_at.year
        ending_at.month = starting_at.month
        ending_at.day = starting_at.day + 1

    if not until_date:
        logger.error(f'Timeslot {timeslot_id} not have a ending date')
        # live_classes.delete()

        return

    delta = relativedelta(0)

    if timeslot.recurrency_type == 'DAILY':
        delta += relativedelta(days=1)

    if timeslot.recurrency_type == 'WEEKLY':
        delta += relativedelta(weeks=1)

    if timeslot.recurrency_type == 'MONTHLY':
        delta += relativedelta(months=1)

    if not delta:
        logger.error(f'{timeslot.recurrency_type} is not a valid or not implemented recurrency_type')
        return

    while True:

        if ending_at > until_date:
            break

        if starting_at > start_date:
            try:
                schedule, _ = LiveClass.objects.get(starting_at=starting_at,
                                                    ending_at=ending_at,
                                                    cohort_time_slot=timeslot)
            except LiveClass.DoesNotExist:
                schedule = LiveClass.objects.create(starting_at=starting_at,
                                                    ending_at=ending_at,
                                                    cohort_time_slot=timeslot,
                                                    remote_meeting_url=cohort.online_meeting_url or '')

            # live_classes = live_classes.exclude(id=schedule.id)

            if not timeslot.recurrent:
                break

        starting_at += delta
        ending_at += delta

    # live_classes.delete()
