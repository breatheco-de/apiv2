import logging

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.admissions.models import CohortTimeSlot
from breathecode.services.eventbrite import Eventbrite
from breathecode.utils import TaskPriority
from breathecode.utils.datetime_integer import DatetimeInteger

from .models import EventbriteWebhook, LiveClass, Organization

logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def mark_live_class_as_started(self, live_class_id: int):
    logger.info(f"Starting mark live class {live_class_id} as started")

    now = timezone.now()

    live_class = LiveClass.objects.filter(id=live_class_id).first()
    if not live_class:
        logger.error(f"Live Class {live_class_id} not fount")
        return

    live_class.started_at = now
    live_class.save()
    return


@shared_task(bind=True, priority=TaskPriority.ACADEMY.value)
def persist_organization_events(self, args):
    from .actions import sync_org_events

    logger.debug("Starting persist_organization_events")
    org = Organization.objects.get(id=args["org_id"])
    sync_org_events(org)
    return True


@shared_task(bind=True, priority=TaskPriority.ACADEMY.value)
def async_eventbrite_webhook(self, eventbrite_webhook_id):
    logger.debug("Starting async_eventbrite_webhook")
    status = "ok"

    webhook = EventbriteWebhook.objects.filter(id=eventbrite_webhook_id).first()
    organization_id = webhook.organization_id
    organization = Organization.objects.filter(id=organization_id).first()

    if organization:
        try:
            client = Eventbrite(organization.eventbrite_key)
            client.execute_action(eventbrite_webhook_id)
        except Exception as e:
            logger.debug("Eventbrite exception")
            logger.debug(str(e))
            status = "error"

    else:
        message = f"Organization {organization_id} doesn't exist"

        webhook.status = "ERROR"
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = "error"

    logger.debug(f"Eventbrite status: {status}")


@shared_task(bind=True, priority=TaskPriority.ACADEMY.value)
def build_live_classes_from_timeslot(self, timeslot_id: int):
    logger.info(f"Starting build_live_classes_from_timeslot with id {timeslot_id}")

    timeslot = CohortTimeSlot.objects.filter(id=timeslot_id).first()
    if not timeslot:
        logger.error(f"Timeslot {timeslot_id} not fount")
        return

    utc_now = timezone.now()

    cohort = timeslot.cohort
    live_classes = LiveClass.objects.filter(cohort_time_slot=timeslot, starting_at__gte=utc_now)

    starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
    ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
    until_date = timeslot.removed_at or cohort.ending_date
    start_date = cohort.kickoff_date

    # this event end in the new day
    while starting_at > ending_at:
        ending_at += relativedelta(days=1)

    if not until_date:
        logger.error(f"Timeslot {timeslot_id} not have a ending date")
        live_classes.delete()

        return

    delta = relativedelta(0)

    if timeslot.recurrency_type == "DAILY":
        delta += relativedelta(days=1)

    if timeslot.recurrency_type == "WEEKLY":
        delta += relativedelta(weeks=1)

    if timeslot.recurrency_type == "MONTHLY":
        delta += relativedelta(months=1)

    if not delta:
        logger.error(f"{timeslot.recurrency_type} is not a valid or not implemented recurrency_type")
        return

    while True:

        if ending_at > until_date:
            break

        if starting_at > start_date:
            schedule, _ = LiveClass.objects.get_or_create(
                starting_at=starting_at,
                ending_at=ending_at,
                cohort_time_slot=timeslot,
                defaults={"remote_meeting_url": cohort.online_meeting_url or ""},
            )

            live_classes = live_classes.exclude(id=schedule.id)

            if not timeslot.recurrent:
                break

        starting_at += delta
        ending_at += delta

    live_classes.delete()


@shared_task(bind=False, priority=TaskPriority.FIXER.value)
def fix_live_class_dates(timeslot_id: int):
    logger.info(f"Starting fix_live_class_dates with id {timeslot_id}")

    timeslot = CohortTimeSlot.objects.filter(id=timeslot_id).first()
    if not timeslot:
        logger.error(f"Timeslot {timeslot_id} not fount")
        return

    utc_now = timezone.now()

    if timeslot.cohort.ending_date and timeslot.cohort.ending_date < utc_now:
        logger.info(f"Cohort {timeslot.cohort.id} is finished")
        return

    cohort = timeslot.cohort
    starting_at = DatetimeInteger.to_utc_datetime(timeslot.timezone, timeslot.starting_at)
    ending_at = DatetimeInteger.to_utc_datetime(timeslot.timezone, timeslot.ending_at)

    # this event end in the new day
    while starting_at > ending_at:
        ending_at += relativedelta(days=1)

    delta = relativedelta(0)

    if timeslot.recurrency_type == "DAILY":
        delta += relativedelta(days=1)

    if timeslot.recurrency_type == "WEEKLY":
        delta += relativedelta(weeks=1)

    if timeslot.recurrency_type == "MONTHLY":
        delta += relativedelta(months=1)

    if not delta:
        logger.error(f"{timeslot.recurrency_type} is not a valid or not implemented recurrency_type")
        return

    for live_class in LiveClass.objects.filter(cohort_time_slot=timeslot).order_by("starting_at"):

        if live_class.starting_at < utc_now or starting_at < cohort.kickoff_date:
            starting_at += delta
            ending_at += delta
            continue

        must_save = False

        if live_class.starting_at != starting_at:
            live_class.starting_at = starting_at
            must_save = True

        if live_class.ending_at != ending_at:
            live_class.ending_at = ending_at
            must_save = True

        if must_save:
            live_class.save()

        starting_at += delta
        ending_at += delta
