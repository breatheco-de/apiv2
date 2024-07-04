import datetime
import logging
from datetime import timedelta

import pytz
from asgiref.sync import sync_to_async
from dateutil.relativedelta import relativedelta
from django.db.models import Q, QuerySet
from django.shortcuts import render
from django.utils import timezone
from google.apps.meet_v2.types import Space, SpaceConfig

import breathecode.activity.tasks as tasks_activity
from breathecode.mentorship.exceptions import ExtendSessionException
from breathecode.services.daily.client import DailyClient
from breathecode.services.google_meet.google_meet import GoogleMeet
from breathecode.utils.datetime_integer import duration_to_str
from capyc.rest_framework.exceptions import ValidationException

from .models import MentorProfile, MentorshipBill, MentorshipService, MentorshipSession

logger = logging.getLogger(__name__)


def close_older_sessions():
    """close the sessions after two hours of ends_at"""

    now = timezone.now()
    diff = timedelta(hours=2)
    sessions = MentorshipSession.objects.filter(status__in=["PENDING", "STARTED"], ends_at__lt=now - diff)

    close_mentoring_sessions(
        sessions,
        {
            "summary": "Automatically closed because its ends was two hours ago or more",
            "status": "FAILED",
        },
    )


def get_pending_sessions_or_create(token, mentor, service, mentee=None):
    close_older_sessions()

    # starting to pick pending sessions
    pending_sessions = []
    if mentee is not None:
        unfinished_with_mentee = MentorshipSession.objects.filter(
            mentor__id=mentor.id, mentee__id=mentee.id, service__id=service.id, status__in=["PENDING", "STARTED"]
        )
        if unfinished_with_mentee.count() > 0:
            pending_sessions += unfinished_with_mentee.values_list("pk", flat=True)

    # if its a mentor, I will force him to close pending sessions
    if mentor.user.id == token.user.id:
        unfinished_sessions = MentorshipSession.objects.filter(
            mentor__id=mentor.id, service__id=service.id, status__in=["PENDING", "STARTED"]
        ).exclude(id__in=pending_sessions)
        # if it has unishined meetings with already started
        if unfinished_sessions.count() > 0:
            pending_sessions += unfinished_sessions.values_list("pk", flat=True)

    # if its a mentee, and there are pending sessions without mentee assigned
    elif mentee is not None and mentee.id == token.user.id:
        unfinished_sessions = MentorshipSession.objects.filter(
            mentor__id=mentor.id, mentee__isnull=True, service__id=service.id, status__in=["PENDING"]
        ).order_by("-mentor_joined_at")

        if unfinished_sessions.count() > 0:
            # grab the last one the mentor joined
            last_one = unfinished_sessions.first()
            pending_sessions += [last_one.id]
            # close the rest
            close_mentoring_sessions(
                unfinished_sessions.exclude(id=last_one.id),
                {
                    "summary": "Automatically closed, not enough information on the meeting the mentor forgot to "
                    "specify the mentee and the mentee never joined",
                    "status": "FAILED",
                },
            )

    # return all the collected pending sessions
    if len(pending_sessions) > 0:
        return MentorshipSession.objects.filter(id__in=pending_sessions)

    # if force_create == True we will try getting from the available unused sessions
    # if I'm here its because there was no previous pending sessions so we will create one

    # default duration can be overridden by service
    duration = timedelta(seconds=3600)
    if service.duration is not None:
        duration = service.duration

    session = MentorshipSession(
        mentor=mentor, mentee=mentee, is_online=True, service=service, ends_at=timezone.now() + duration
    )

    if session.service.video_provider == MentorshipService.VideoProvider.GOOGLE_MEET:
        create_room_on_google_meet(session)

    elif session.service.video_provider == MentorshipService.VideoProvider.DAILY:
        daily = DailyClient()
        room = daily.create_room(exp_in_seconds=service.duration.seconds)
        session.online_meeting_url = room["url"]
        session.name = room["name"]
        session.mentee = mentee
        session.save()

    else:
        raise Exception("Invalid video provider")

    if mentee:
        tasks_activity.add_activity.delay(
            mentee.id, "mentorship_session_checkin", related_type="mentorship.MentorshipSession", related_id=session.id
        )

    return MentorshipSession.objects.filter(id=session.id)


def extend_session(session: MentorshipSession, duration_in_minutes=None, exp_in_epoch=None, tz=pytz.UTC):

    if not session.name:
        raise ExtendSessionException("Can't extend sessions not have a name")

    # make 30min default for both
    if duration_in_minutes is None and exp_in_epoch is None:
        duration_in_minutes = 30

    # default duration can be overridden by service
    daily = DailyClient()

    if duration_in_minutes is not None and session.ends_at:
        daily.extend_room(name=session.name, exp_in_seconds=duration_in_minutes * 3600)
        session.ends_at = session.ends_at + timedelta(minutes=duration_in_minutes)
    elif exp_in_epoch is not None:
        daily.extend_room(name=session.name, exp_in_epoch=exp_in_epoch)
        session.ends_at = datetime.datetime.fromtimestamp(exp_in_epoch, tz)

    session.save()
    return MentorshipSession.objects.filter(id=session.id)


def render_session(request, session, token):
    from .serializers import GETSessionReportSerializer

    data = {
        "subject": session.service.name,
        "room_url": session.online_meeting_url,
        "session": GETSessionReportSerializer(session, many=False).data,
        "userName": (token.user.first_name + " " + token.user.last_name).strip(),
        "backup_room_url": session.mentor.online_meeting_url,
    }

    if token.user.id == session.mentor.user.id:
        data["leave_url"] = "/mentor/session/" + str(session.id) + "?token=" + token.key
    else:
        data["leave_url"] = "close"

    return render(request, "daily.html", data)


def close_mentoring_sessions(sessions: QuerySet[MentorshipSession], data: dict):
    for session in sessions:
        close_mentoring_session(session, data)


def close_mentoring_session(session: MentorshipSession, data: dict):
    sessions_to_close = MentorshipSession.objects.filter(id=session.id)
    sessions_to_close.update(summary=data["summary"], status=data["status"].upper(), ended_at=timezone.now())

    return sessions_to_close


def get_accounted_time(_session):

    def get_duration(session):
        response = {"accounted_duration": 0, "status_message": ""}
        if session.started_at is None and session.mentor_joined_at is not None:
            response["status_message"] = "Mentor joined but mentee never did, "
            if session.service.missed_meeting_duration.seconds > 0:
                response["accounted_duration"] = session.service.missed_meeting_duration
                response["status_message"] += (
                    f'{duration_to_str(response["accounted_duration"])} will be ' "accounted for the bill."
                )
            else:
                response["accounted_duration"] = timedelta(seconds=0)
                response["status_message"] += "No time will be included on the bill."
            return response

        elif session.started_at is not None:

            if session.mentor_joined_at is None:
                response["accounted_duration"] = timedelta(seconds=0)
                response["status_message"] = "The mentor never joined the meeting, no time will " "be accounted for."
                return response

            if session.ended_at is None:
                if session.ends_at is not None and session.ends_at > session.started_at:
                    response["accounted_duration"] = session.ends_at - session.started_at
                    response["status_message"] = (
                        "The session never ended, accounting for the expected meeting duration "
                        f'that was {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
                elif session.mentee_left_at is not None:
                    response["accounted_duration"] = session.mentee_left_at - session.started_at
                    response["status_message"] = (
                        "The session never ended, accounting duration based on the time where "
                        f'the mentee left the meeting {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
                elif session.mentor_left_at is not None:
                    response["accounted_duration"] = session.mentor_left_at - session.started_at
                    response["status_message"] = (
                        "The session never ended, accounting duration based on the time where the mentor "
                        f'left the meeting {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
                else:
                    response["accounted_duration"] = session.service.duration
                    response["status_message"] = (
                        "The session never ended, accounting for the standard duration "
                        f'{duration_to_str(response["accounted_duration"])}.'
                    )
                    return response

            if session.started_at > session.ended_at:
                response["accounted_duration"] = timedelta(seconds=0)
                response["status_message"] = "Meeting started before it ended? No duration " "will be accounted for."
                return response

            if (session.ended_at - session.started_at).days >= 1:
                if session.mentee_left_at is not None:
                    response["accounted_duration"] = session.mentee_left_at - session.started_at
                    response["status_message"] = (
                        "The lasted way more than it should, accounting duration based on the time where "
                        f'the mentee left the meeting {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
                else:
                    response["accounted_duration"] = session.service.duration
                    response["status_message"] = (
                        "This session lasted more than a day, no one ever left, was probably never closed, "
                        f'accounting for standard duration {duration_to_str(response["accounted_duration"])}'
                        "."
                    )
                    return response

            response["accounted_duration"] = session.ended_at - session.started_at
            if response["accounted_duration"] > session.service.max_duration:
                if session.service.max_duration.seconds == 0:
                    response["accounted_duration"] = session.service.duration
                    response["status_message"] = (
                        "No extra time is allowed for session, accounting for standard duration "
                        f'of {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
                else:
                    response["accounted_duration"] = session.service.max_duration
                    response["status_message"] = (
                        "The duration of the session is bigger than the maximum allowed, accounting "
                        f'for max duration of {duration_to_str(response["accounted_duration"])}.'
                    )
                    return response
            else:
                # everything perfect, we account for the expected
                return response

        else:
            response["accounted_duration"] = timedelta(seconds=0)
            response["status_message"] = "No one joined this session, nothing will be accounted for."
            return response

    _duration = get_duration(_session)
    if _duration["accounted_duration"] > _session.service.max_duration:
        _duration["accounted_duration"] = _session.service.max_duration
        _duration["status_message"] += (
            " The session accounted duration was limited to the maximum allowed "
            f'{duration_to_str(_duration["accounted_duration"])}.'
        )
    return _duration


def last_month_date(current_date):
    # getting next month
    # using replace to get to last day + offset
    # to reach next month
    nxt_mnth = current_date.replace(day=28, hour=23, minute=59, second=59, microsecond=999999) + datetime.timedelta(
        days=4
    )

    # subtracting the days from next month date to
    # get last date of current Month
    last_datetime = nxt_mnth - datetime.timedelta(days=nxt_mnth.day)

    return last_datetime


def generate_mentor_bills(mentor, reset=False):
    bills = []

    def get_unpaid_sessions():
        return MentorshipSession.objects.filter(
            Q(bill__isnull=True)
            | Q(bill__status="DUE", bill__academy=mentor.academy, bill__paid_at__isnull=True)
            | Q(bill__status="RECALCULATE", bill__academy=mentor.academy, bill__paid_at__isnull=True),
            service__isnull=False,
            allow_billing=True,
            mentor__id=mentor.id,
            status__in=["COMPLETED", "FAILED"],
            started_at__isnull=False,
        ).order_by("started_at")

    without_service = MentorshipSession.objects.filter(
        Q(bill__isnull=True)
        | Q(bill__status="DUE", bill__academy=mentor.academy, bill__paid_at__isnull=True)
        | Q(bill__status="RECALCULATE", bill__academy=mentor.academy, bill__paid_at__isnull=True),
        mentor=mentor,
        service__isnull=True,
    ).count()
    if without_service:
        raise ValidationException(
            f"This mentor has {without_service} sessions without an associated service that need to be fixed",
            slug="session_without_service",
        )

    recalculate_bills = MentorshipBill.objects.filter(
        Q(status="DUE") | Q(status="RECALCULATE"), mentor__id=mentor.id, academy__id=mentor.academy.id
    )

    unpaid_sessions = get_unpaid_sessions()
    if not unpaid_sessions:
        if recalculate_bills:
            for bill in recalculate_bills:
                bill.status = "DUE"
                bill.save()
        return []

    pending_months = sorted({(x.year, x.month) for x in unpaid_sessions.values_list("started_at", flat=True)})
    for year, month in pending_months:
        sessions_of_month = unpaid_sessions.filter(started_at__month=month, started_at__year=year)

        start_at = datetime.datetime(year, month, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)
        end_at = (
            datetime.datetime(year, month, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)
            + relativedelta(months=1)
            - datetime.timedelta(microseconds=1)
        )

        open_bill = None
        if recalculate_bills:
            open_bill = recalculate_bills.filter(started_at__month=month, started_at__year=year).first()

        if open_bill is None:
            open_bill = MentorshipBill(mentor=mentor, academy=mentor.academy, started_at=start_at, ended_at=end_at)
            open_bill.save()
        else:
            open_bill.status = "DUE"

        open_bill = generate_mentor_bill(mentor, open_bill, sessions_of_month, reset)

        bills.append(open_bill)

    return bills


def generate_mentor_bill(mentor, bill, sessions, reset=False):
    total = {"minutes": 0, "overtime_minutes": 0}

    for session in sessions:
        session.bill = bill

        _result = get_accounted_time(session)

        session.suggested_accounted_duration = _result["accounted_duration"]
        session.status_message = _result["status_message"]

        # if is null and reset=true all the sessions durations will be rest to the suggested one
        if session.accounted_duration is None or reset == True:
            session.accounted_duration = _result["accounted_duration"]

        extra_minutes = 0
        if session.accounted_duration > session.service.duration:
            extra_minutes = (session.accounted_duration - session.service.duration).seconds / 60

        total["minutes"] = total["minutes"] + (session.accounted_duration.seconds / 60)
        total["overtime_minutes"] = total["overtime_minutes"] + extra_minutes

        session.save()

    total["hours"] = round(total["minutes"] / 60, 2)
    total["price"] = total["hours"] * mentor.price_per_hour

    bill.total_duration_in_hours = total["hours"]
    bill.total_duration_in_minutes = total["minutes"]
    bill.overtime_minutes = total["overtime_minutes"]
    bill.total_price = total["price"]
    bill.save()

    return bill


def mentor_is_ready(mentor: MentorProfile):

    if mentor.online_meeting_url is None or mentor.online_meeting_url == "":
        raise Exception(
            f"Mentor {mentor.name} does not have backup online_meeting_url, update the value before activating."
        )

    elif mentor.booking_url is None or "https://calendly.com" not in mentor.booking_url:
        raise Exception(f"Mentor {mentor.name} booking_url must point to calendly, update the value before activating.")

    elif len(mentor.syllabus.all()) == 0:
        raise Exception(f"Mentor {mentor.name} has no syllabus associated, update the value before activating.")

    elif "no-booking-url" not in mentor.availability_report and "bad-booking-url" in mentor.availability_report:
        raise Exception(f"Mentor {mentor.name} booking URL is failing.")

    elif (
        "no-online-meeting-url" not in mentor.availability_report
        and "bad-online-meeting-url" in mentor.availability_report
    ):
        raise Exception(f"Mentor {mentor.name} online meeting URL is failing.")

    return True


def create_room_on_google_meet(session: MentorshipSession) -> None:
    """Create a room on google meet for a mentorship session."""

    if isinstance(session, MentorshipSession) is False:
        raise Exception("session argument must be a MentorshipSession")

    if session.service.video_provider != session.service.VideoProvider.GOOGLE_MEET:
        raise Exception("Video provider must be Google Meet")

    if not session.service:
        raise Exception("Mentorship session doesn't have a service associated with it")

    mentor = session.mentor

    meet = GoogleMeet()
    if session.id is None:
        session.save()

    title = f"{session.service.name} {session.id} | " f"{mentor.user.first_name} {mentor.user.last_name}"
    s = Space(
        name=title,
        config=SpaceConfig(access_type=SpaceConfig.AccessType.OPEN),
    )
    space = meet.create_space(space=s)
    session.online_meeting_url = space.meeting_uri
    session.name = title
    session.save()


@sync_to_async
def acreate_room_on_google_meet(session: MentorshipSession) -> None:
    return create_room_on_google_meet(session)
