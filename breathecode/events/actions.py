import functools
import logging
import os
import re
from datetime import datetime, timedelta

import pytz
from django.db.models import QuerySet
from django.db.models.query_utils import Q
from django.utils import timezone

from breathecode.admissions.models import Cohort, CohortTimeSlot, CohortUser, TimeSlot
from breathecode.payments.models import AbstractIOweYou, PlanFinancing, Subscription
from breathecode.utils.datetime_integer import DatetimeInteger

from .models import Event, EventType, Organization, Organizer, Venue
from .utils import Eventbrite

logger = logging.getLogger(__name__)

status_map = {
    "draft": "DRAFT",
    "live": "ACTIVE",
    "completed": "COMPLETED",
    "started": "ACTIVE",
    "ended": "ACTIVE",
    "canceled": "DELETED",
}


def get_my_event_types(_user):

    def build_query_params(cohort=None, syllabus=None, academy=None):
        """
        Build the query params to the visibility options.
        """

        return {
            "visibility_settings__cohort": cohort,
            "visibility_settings__syllabus": syllabus,
            "visibility_settings__academy": academy,
        }

    def get_related_resources():
        """
        Get the resources related to this user.
        """

        def process_i_owe_you(i_owe_them: QuerySet[AbstractIOweYou]):
            for i_owe_you in i_owe_them:
                if (
                    i_owe_you.selected_cohort_set
                    and i_owe_you.selected_cohort_set.cohorts.first().academy
                    and i_owe_you.selected_cohort_set.cohorts.first().academy not in academies
                ):
                    academies.append(i_owe_you.selected_cohort_set.cohorts.first().academy)

                if i_owe_you.selected_cohort_set and i_owe_you.selected_cohort_set.cohorts.first() not in cohorts:
                    cohorts.append(i_owe_you.selected_cohort_set.cohorts.first())

                if (
                    i_owe_you.selected_cohort_set
                    and i_owe_you.selected_cohort_set.cohorts.first().syllabus_version
                    and i_owe_you.selected_cohort_set.cohorts.first().syllabus_version.syllabus not in syllabus
                ):
                    syllabus.append(
                        {
                            "syllabus": i_owe_you.selected_cohort_set.cohorts.first().syllabus_version.syllabus,
                            "academy": i_owe_you.selected_cohort_set.cohorts.first().academy,
                        }
                    )

                if i_owe_you.selected_event_type_set and i_owe_you.selected_event_type_set.academy not in academies:
                    academies.append(i_owe_you.selected_event_type_set.academy)

                if (
                    i_owe_you.selected_mentorship_service_set
                    and i_owe_you.selected_mentorship_service_set.academy not in academies
                ):
                    academies.append(i_owe_you.selected_mentorship_service_set.academy)

                if i_owe_you.selected_event_type_set:
                    for event_type in i_owe_you.selected_event_type_set.event_types.all():
                        if event_type.id not in ids:
                            ids.append(event_type.id)

        syllabus = []
        academies = []
        cohorts = []
        ids = []

        utc_now = timezone.now()
        statuses = ["CANCELLED", "DEPRECATED"]
        at_least_one_resource_linked = (
            Q(selected_cohort_set__isnull=False)
            | Q(selected_mentorship_service_set__isnull=False)
            | Q(selected_event_type_set__isnull=False)
        )

        cohort_users = CohortUser.objects.filter(user=_user)
        cohort_users_with_syllabus = cohort_users.filter(cohort__syllabus_version__isnull=False)

        subscriptions = Subscription.objects.filter(
            at_least_one_resource_linked, Q(valid_until=None) | Q(valid_until__gte=utc_now), user=_user
        ).exclude(status__in=statuses)

        plan_financings = PlanFinancing.objects.filter(
            at_least_one_resource_linked, valid_until__gte=utc_now, user=_user
        ).exclude(status__in=statuses)

        for cohort_user in cohort_users_with_syllabus:
            if cohort_user.cohort.syllabus_version.syllabus not in cohorts:
                syllabus.append(
                    {
                        "syllabus": cohort_user.cohort.syllabus_version.syllabus,
                        "academy": cohort_user.cohort.academy,
                    }
                )

        for cohort_user in cohort_users:
            if cohort_user.cohort.academy not in cohorts:
                academies.append(cohort_user.cohort.academy)

        for cohort_user in cohort_users:
            if cohort_user.cohort not in cohorts:
                cohorts.append(cohort_user.cohort)

        process_i_owe_you(subscriptions)
        process_i_owe_you(plan_financings)

        return academies, cohorts, syllabus, ids

    def my_events():

        query = None
        academies, cohorts, syllabus, ids = get_related_resources()

        # shared with the whole academy
        for academy in academies:
            kwargs = build_query_params(academy=academy)
            if query:
                query |= Q(**kwargs, academy=academy) | Q(**kwargs, allow_shared_creation=True)
            else:
                query = Q(**kwargs, academy=academy) | Q(**kwargs, allow_shared_creation=True)

        # shared with a specific cohort
        for cohort in cohorts:
            kwargs = build_query_params(academy=cohort.academy, cohort=cohort)
            # is not necessary provided the syllabus
            if query:
                query |= Q(**kwargs, academy=cohort.academy) | Q(**kwargs, allow_shared_creation=True)
            else:
                query = Q(**kwargs, academy=cohort.academy) | Q(**kwargs, allow_shared_creation=True)

        # shared with a specific syllabus
        for s in syllabus:
            kwargs = build_query_params(academy=s["academy"], syllabus=s["syllabus"])
            if query:
                query |= Q(**kwargs, academy=s["academy"]) | Q(**kwargs, allow_shared_creation=True)
            else:
                query = Q(**kwargs, academy=s["academy"]) | Q(**kwargs, allow_shared_creation=True)

        if ids:
            if query:
                query |= Q(id__in=ids)
            else:
                query = Q(id__in=ids)

        if query:
            return EventType.objects.filter(query)
        else:
            return EventType.objects.none()

    return my_events()


def sync_org_venues(org):
    if org.academy is None:
        raise Exception("First you must specify to which academy this organization belongs")

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_venues(org.eventbrite_id)

    for data in result["venues"]:
        create_or_update_venue(data, org, force_update=True)

    return True


def create_or_update_organizer(data, org, force_update=False):
    if org.academy is None:
        raise Exception("First you must specify to which academy this organization belongs")

    organizer = Organizer.objects.filter(eventbrite_id=data["id"]).first()

    try:
        if organizer is None:
            organizer = Organizer(
                name=data["name"], description=data["description"]["text"], eventbrite_id=data["id"], organization=org
            )
            organizer.save()

        elif force_update == True:
            organizer.name = data["name"]
            organizer.description = data["description"]["text"]
            organizer.save()

    except Exception as e:
        print("Error saving organizer eventbrite_id: " + str(data["id"]) + " skipping to the next", e)

    return organizer


def create_or_update_venue(data, org, force_update=False):
    if not org.academy:
        logger.error(f"The organization {org} not have a academy assigned")
        return

    venue = Venue.objects.filter(eventbrite_id=data["id"], academy__id=org.academy.id).first()

    if venue and not force_update:
        return

    kwargs = {
        "title": data["name"],
        "street_address": data["address"]["address_1"],
        "country": data["address"]["country"],
        "city": data["address"]["city"],
        "state": data["address"]["region"],
        "zip_code": data["address"]["postal_code"],
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "eventbrite_id": data["id"],
        "eventbrite_url": data["resource_uri"],
        "academy": org.academy,
        # 'organization': org,
    }

    try:
        if venue is None:
            Venue(**kwargs).save()

        elif force_update == True:
            for attr in kwargs:
                setattr(venue, attr, kwargs[attr])

            venue.save()

    except Exception:
        logger.error(f'Error saving venue eventbrite_id: {data["id"]} skipping to the next')

    return venue


def export_event_description_to_eventbrite(event: Event) -> None:
    if not event:
        logger.error("Event is not being provided")
        return

    if not event.eventbrite_id:
        logger.error(f"Event {event.id} not have the integration with eventbrite")
        return

    if not event.organization:
        logger.error(f"Event {event.id} not have a organization assigned")
        return

    if not event.description:
        logger.warning(f"The event {event.id} not have description yet")
        return

    eventbrite_id = event.eventbrite_id
    client = Eventbrite(event.organization.eventbrite_key)

    payload = {
        "modules": [
            {
                "type": "text",
                "data": {
                    "body": {
                        "type": "text",
                        "text": event.description,
                        "alignment": "left",
                    },
                },
            }
        ],
        "publish": True,
        "purpose": "listing",
    }

    try:
        structured_content = client.get_event_description(eventbrite_id)
        result = client.create_or_update_event_description(
            eventbrite_id, structured_content["page_version_number"], payload
        )

        if not result["modules"]:
            error = "Could not create event description in eventbrite"
            logger.error(error)

            event.eventbrite_sync_description = error
            event.eventbrite_sync_status = "ERROR"
            event.save()

        else:
            event.eventbrite_sync_description = timezone.now()
            event.eventbrite_sync_status = "SYNCHED"
            event.save()

    except Exception as e:
        error = str(e)
        logger.error(error)

        event.eventbrite_sync_description = error
        event.eventbrite_sync_status = "ERROR"
        event.save()


def export_event_to_eventbrite(event: Event, org: Organization):
    if not org.academy:
        logger.error(f"The organization {org} not have a academy assigned")
        return

    timezone = org.academy.timezone
    client = Eventbrite(org.eventbrite_key)
    now = get_current_iso_string()

    data = {
        "event.name.html": event.title,
        "event.description.html": event.description,
        "event.start.utc": re.sub(r"\+00:00$", "Z", event.starting_at.isoformat()),
        "event.end.utc": re.sub(r"\+00:00$", "Z", event.ending_at.isoformat()),
        # 'event.summary': event.excerpt,
        "event.capacity": event.capacity,
        "event.online_event": event.online_event,
        "event.url": event.eventbrite_url,
        "event.currency": event.currency,
    }

    if event.eventbrite_organizer_id:
        data["event.organizer_id"] = event.eventbrite_organizer_id

    if timezone:
        data["event.start.timezone"] = timezone
        data["event.end.timezone"] = timezone

    try:
        if event.eventbrite_id:
            client.update_organization_event(event.eventbrite_id, data)

        else:
            result = client.create_organization_event(org.eventbrite_id, data)
            event.eventbrite_id = str(result["id"])

        event.eventbrite_sync_description = now
        event.eventbrite_sync_status = "SYNCHED"

        export_event_description_to_eventbrite(event)

    except Exception as e:
        event.eventbrite_sync_description = f"{now} => {e}"
        event.eventbrite_sync_status = "ERROR"

    event.save()
    return event


def sync_org_events(org):
    if not org.academy:
        logger.error(f"The organization {org} not have a academy assigned")
        return

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_events(org.eventbrite_id)

    try:

        for data in result["events"]:
            update_or_create_event(data, org)

        org.sync_status = "PERSISTED"
        org.sync_desc = f"Success with {len(result['events'])} events..."
        org.save()

    except Exception as e:
        if org:
            org.sync_status = "ERROR"
            org.sync_desc = "Error: " + str(e)
            org.save()
        raise e

    events = Event.objects.filter(sync_with_eventbrite=True, eventbrite_sync_status="PENDING")
    for event in events:
        export_event_to_eventbrite(event, org)

    return True


# use for mocking purpose
def get_current_iso_string():
    from django.utils import timezone

    return str(timezone.now())


def update_event_description_from_eventbrite(event: Event) -> None:
    if not event:
        logger.error("Event is not being provided")
        return

    if not event.eventbrite_id:
        logger.error(f"Event {event.id} not have the integration with eventbrite")
        return

    if not event.organization:
        logger.error(f"Event {event.id} not have a organization assigned")
        return

    eventbrite_id = event.eventbrite_id
    client = Eventbrite(event.organization.eventbrite_key)

    try:
        data = client.get_event_description(eventbrite_id)
        event.description = data["modules"][0]["data"]["body"]["text"]
        event.eventbrite_sync_description = timezone.now()
        event.eventbrite_sync_status = "PERSISTED"
        event.save()

    except Exception:
        error = f"The event {eventbrite_id} is coming from eventbrite not have a description"
        logger.warning(error)
        event.eventbrite_sync_description = error
        event.eventbrite_sync_status = "ERROR"


def update_or_create_event(data, org):
    if data is None:  # skip if no data
        logger.warning("Ignored event")
        return False

    if not org.academy:
        logger.error(f"The organization {org} not have a academy assigned")
        return

    now = get_current_iso_string()

    if data["status"] not in status_map:
        raise Exception("Uknown eventbrite status " + data["status"])

    event = Event.objects.filter(eventbrite_id=data["id"], organization__id=org.id).first()
    try:
        venue = None
        if "venue" in data and data["venue"] is not None:
            venue = create_or_update_venue(data["venue"], org)
        organizer = None
        if "organizer" in data and data["organizer"] is not None:
            organizer = create_or_update_organizer(data["organizer"], org, force_update=True)
        else:
            print("Event without organizer", data)

        kwargs = {
            "title": data["name"]["text"],
            "excerpt": data["description"]["text"],
            "starting_at": data["start"]["utc"],
            "ending_at": data["end"]["utc"],
            "capacity": data["capacity"],
            "online_event": data["online_event"],
            "eventbrite_id": data["id"],
            "eventbrite_url": data["url"],
            "status": status_map[data["status"]],
            "eventbrite_status": data["status"],
            "currency": data["currency"],
            "organization": org,
            # organizer: organizer,
            "venue": venue,
        }

        if event is None:
            event = Event(**kwargs)
            event.sync_with_eventbrite = True

        else:
            for attr in kwargs:
                setattr(event, attr, kwargs[attr])

        if "published" in data:
            event.published_at = data["published"]

        if "logo" in data and data["logo"] is not None:
            event.banner = data["logo"]["url"]

        if not event.url:
            event.url = event.eventbrite_url

        # look for the academy ownership based on organizer first
        if organizer is not None and organizer.academy is not None:
            event.academy = organizer.academy

        elif org.academy is not None:
            event.academy = org.academy

        event.eventbrite_sync_description = now
        event.eventbrite_sync_status = "PERSISTED"
        event.save()

        update_event_description_from_eventbrite(event)

    except Exception as e:
        if event is not None:
            event.eventbrite_sync_description = f"{now} => {e}"
            event.eventbrite_sync_status = "ERROR"
            event.save()
        raise e

    return event


def publish_event_from_eventbrite(data, org: Organization) -> None:
    if not data:  # skip if no data
        logger.info("Ignored event")
        raise ValueError("data is empty")

    now = get_current_iso_string()

    try:
        events = Event.objects.filter(eventbrite_id=data["id"], organization__id=org.id)
        if events.count() == 0:
            raise Warning(f'The event with the eventbrite id `{data["id"]}` doesn\'t exist')

        for event in events:
            event.status = "ACTIVE"
            event.eventbrite_status = data["status"]
            event.eventbrite_sync_description = now
            event.eventbrite_sync_status = "PERSISTED"
            event.save()
            logger.info(f'The events with the eventbrite id `{data["id"]}` were saved')
        return events.first()

    except Warning as e:
        logger.error(f"{now} => {e}")
        raise e

    except Exception as e:
        logger.exception(f"{now} => the body is coming from eventbrite has change")
        raise e


def datetime_in_range(start: datetime, end: datetime, current: datetime):
    """
    Check if a datetime is in the range.

    Usages:

    ```py
    from django.utils import timezone
    from datetime import timedelta

    utc_now = timezone.now()
    start = utc_now - timedelta(days=1)
    end = utc_now + timedelta(days=1)

    datetime_in_range(start, end, utc_now)  # returns 0, the datetime is in the range

    utc_now = utc_now - timedelta(days=2)
    datetime_in_range(start, end, utc_now)  # returns -1, the datetime is less than start

    utc_now = utc_now + timedelta(days=4)
    datetime_in_range(start, end, utc_now)  # returns 1, the datetime is greater than start
    ```
    """

    if current < start:
        return -1

    if current > end:
        return 1

    return 0


def update_timeslots_out_of_range(start: datetime, end: datetime, timeslots: QuerySet[TimeSlot]):
    """
    Get a list of timeslots in the range.

    Usages:

    ```py
    from django.utils import timezone
    from datetime import timedelta

    start = utc_now - timedelta(days=1)
    end = utc_now + timedelta(days=1)
    queryset = ...

    update_timeslots_out_of_range(start, end, queryset)  # returns a list of timeslots
    ```
    """

    lists = []

    for timeslot in timeslots:
        starting_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.starting_at)
        ending_at = DatetimeInteger.to_datetime(timeslot.timezone, timeslot.ending_at)
        delta = ending_at - starting_at

        n1 = datetime_in_range(start, end, starting_at)
        n2 = datetime_in_range(start, end, ending_at)

        less_than_start = n1 == -1 or n2 == -1
        greater_than_end = n2 == 1 or n2 == 1

        if not timeslot.recurrent and (less_than_start or greater_than_end):
            continue

        if less_than_start:
            starting_at = fix_datetime_weekday(start, starting_at, next=True)
            ending_at = starting_at + delta

        elif greater_than_end:
            ending_at = fix_datetime_weekday(end, ending_at, prev=True)
            starting_at = ending_at - delta

        lists.append(
            {
                **vars(timeslot),
                "starting_at": starting_at,
                "ending_at": ending_at,
            }
        )

    return sorted(lists, key=lambda x: (x["starting_at"], x["ending_at"]))


def fix_datetime_weekday(current: datetime, timeslot: datetime, prev: bool = False, next: bool = False) -> datetime:
    if not prev and not next:
        raise Exception("You should provide a prev or next argument")

    days = 0
    weekday = timeslot.weekday()
    postulate = datetime(
        year=current.year,
        month=current.month,
        day=current.day,
        hour=timeslot.hour,
        minute=timeslot.minute,
        second=timeslot.second,
        tzinfo=timeslot.tzinfo,
    )

    while True:
        if prev:
            res = postulate - timedelta(days=days)
            if weekday == res.weekday():
                return res

        if next:
            res = postulate + timedelta(days=days)
            if weekday == res.weekday():
                return res

        days = days + 1


RECURRENCY_TYPE = {
    "DAILY": "day",
    "WEEKLY": "week",
    "MONTHLY": "month",
}


def get_cohort_description(timeslot: CohortTimeSlot) -> str:
    description = ""

    if timeslot.recurrent:
        description += f"every {RECURRENCY_TYPE[timeslot.recurrency_type]}, "

    localtime = pytz.timezone(timeslot.cohort.academy.timezone)

    starting_at = localtime.localize(timeslot.starting_at)
    ending_at = localtime.localize(timeslot.ending_at)

    starting_weekday = starting_at.strftime("%A").upper()
    ending_weekday = ending_at.strftime("%A").upper()

    if starting_weekday == ending_weekday:
        description += f"{starting_weekday}"

    else:
        description += f"{starting_weekday} and {ending_weekday} "

    starting_hour = starting_at.strftime("%I:%M %p")
    ending_hour = ending_at.strftime("%I:%M %p")
    description += f"from {starting_hour} to {ending_hour}"

    return description.capitalize()


def get_ical_cohort_description(item: Cohort):
    description = ""
    # description = f'{description}Url: {item.url}\n'

    if item.name:
        description = f"{description}Name: {item.name}\n"

    if item.academy:
        description = f"{description}Academy: {item.academy.name}\n"

    if item.language:
        description = f"{description}Language: {item.language.upper()}\n"

    if item.private:
        description = f'{description}Private: {"Yes" if item.private else "No"}\n'

    if item.remote_available:
        description = f'{description}Online: {"Yes" if item.remote_available else "No"}\n'

    # TODO: add private url to meeting url

    return description


@functools.lru_cache(maxsize=1)
def is_eventbrite_enabled():
    if "ENV" in os.environ and os.environ["ENV"] == "test":
        return True

    return os.getenv("EVENTBRITE", "0") == "1"
