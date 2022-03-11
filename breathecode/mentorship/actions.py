import os, re, json, logging, time, datetime
from itertools import chain
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from breathecode.services.daily.client import DailyClient
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from .models import MentorshipSession, MentorshipBill
from .serializers import GETSessionReportSerializer
from breathecode.utils.datetime_interger import duration_to_str

logger = logging.getLogger(__name__)


def get_or_create_sessions(token, mentor, mentee=None, force_create=False):

    # default duration can be ovveriden by service
    duration = timedelta(seconds=3600)
    if mentor.service.duration is not None:
        duration = mentor.service.duration

    if mentee is not None and force_create == False:
        unfinished_with_mentee = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                                  mentee__id=mentee.id,
                                                                  status__in=['PENDING', 'STARTED'])
        if unfinished_with_mentee.count() > 0:
            return unfinished_with_mentee

    if force_create == False:
        # session without mentee
        unfinished_without_mentee = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                                     started_at__isnull=True,
                                                                     status__in=['PENDING', 'STARTED'])
        # delete the pendings ones, its worth creating a new meeting
        if unfinished_without_mentee.count() > 0:
            session = unfinished_without_mentee.first()
            session.mentee = mentee
            session.save()

            # extend the session now that the mentee has joined
            exp_in_epoch = time.mktime((timezone.now() + duration).timetuple())
            extend_session(session, exp_in_epoch=exp_in_epoch)

            unfinished_without_mentee.exclude(id=session.id).delete()
            return MentorshipSession.objects.filter(id=session.id)

    # if its a mentor, I will force him to close pending sessions
    if mentor.user.id == token.user.id and not force_create:
        unfinished_with_mentee = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                                  status__in=['PENDING', 'STARTED'])

        # if it has unishined meetings with already started
        if unfinished_with_mentee.count() > 0:
            return unfinished_with_mentee

    # if force_create == True we will try getting from the available unnused sessions
    # if I'm here its because there was no previous pending sessions so we will create one

    session = MentorshipSession(mentor=mentor,
                                mentee=mentee,
                                is_online=True,
                                ends_at=timezone.now() + duration)
    daily = DailyClient()
    room = daily.create_room(exp_in_seconds=mentor.service.duration.seconds)
    session.online_meeting_url = room['url']
    session.name = room['name']
    session.mentee = mentee

    session.save()
    return MentorshipSession.objects.filter(id=session.id)


def extend_session(session, duration_in_minutes=None, exp_in_epoch=None):

    # make 30min default for both
    if duration_in_minutes is None and exp_in_epoch is None:
        duration_in_minutes = 30

    # default duration can be ovveriden by service
    daily = DailyClient()

    if duration_in_minutes is not None:
        room = daily.extend_room(name=session.name, exp_in_seconds=duration_in_minutes * 3600)
        session.ends_at = session.ends_at + timedelta(minutes=duration_in_minutes)
    elif exp_in_epoch is not None:
        room = daily.extend_room(name=session.name, exp_in_epoch=exp_in_epoch)
        session.ends_at = datetime.datetime.fromtimestamp(exp_in_epoch)

    session.save()
    return MentorshipSession.objects.filter(id=session.id)


def render_session(request, session, token):

    data = {
        'subject': session.mentor.service.name,
        'room_url': session.online_meeting_url,
        'session': GETSessionReportSerializer(session, many=False).data,
        'userName': (token.user.first_name + ' ' + token.user.last_name).strip(),
        'backup_room_url': session.mentor.online_meeting_url,
    }

    if token.user.id == session.mentor.user.id:
        data['leave_url'] = '/mentor/session/' + str(session.id) + '?token=' + token.key
    else:
        data['leave_url'] = 'close'

    return render(request, 'daily.html', data)


def close_mentoring_session(session, data):

    session.summary = data['summary']
    session.status = data['status'].upper()
    session.ended_at = timezone.now()
    session.save()

    # Close sessions from the same mentor that expired and the mentee never joined
    MentorshipSession.objects.filter(mentor__id=session.mentor.id,
                                     status__in=['PENDING', 'STARTED'],
                                     ended_at__lte=timezone.now(),
                                     started_at__isnull=True).update(
                                         status='FAILED',
                                         summary='Meeting automatically closed, mentee never joined.')

    return session


def add_accounted_time(session, reset=False):

    # only calculate accounted duration if its null
    if session.accounted_duration is not None and reset == False:
        return session

    session.status_message = ''
    if session.started_at is None and session.mentor_joined_at is not None:
        session.status_message = 'Mentor joined but mentee never did, '
        if session.mentor.service.missed_meeting_duration.seconds > 0:
            session.accounted_duration = session.mentor.service.missed_meeting_duration
            session.status_message += f'{duration_to_str(session.accounted_duration)} will be accounted for the bill.'
        else:
            session.accounted_duration = timedelta(seconds=0)
            session.status_message += f'No time will be included on the bill.'
        return session

    elif session.started_at is not None:

        if session.mentor_joined_at is None:
            session.accounted_duration = timedelta(seconds=0)
            session.status_message = 'The mentor never joined the meeting, no time will be accounted for.'
            return session

        if session.ended_at is None:
            if obj.ends_at is not None and session.ends_at > session.started_at:
                session.accounted_duration = session.ends_at - session.started_at
                session.status_message = f'The session never ended, accounting for the expected meeting duration that was {duration_to_str(session.accounted_duration)}.'
                return session
            elif session.mentee_left_at is not None:
                session.accounted_duration = session.mentee_left_at - session.started_at
                session.status_message = f'The session never ended, accounting duration based on the time where the mentee left the meeting {duration_to_str(session.accounted_duration)}.'
                return session
            elif session.mentor_left_at is not None:
                session.accounted_duration = session.mentor_left_at - session.started_at
                session.status_message = f'The session never ended, accounting duration based on the time where the mentor left the meeting {duration_to_str(session.accounted_duration)}.'
                return session
            else:
                session.accounted_duration = session.mentor.service.duration
                session.status_message = f'The session never ended, accounting for the standard duration {duration_to_str(session.accounted_duration)}.'
                return session

        if session.started_at > session.ended_at:
            session.accounted_duration = timedelta(seconds=0)
            session.status_message = 'Meeting started before it ended? No duration will be accounted for.'
            return session

        if (session.ended_at - session.started_at).days > 1:
            if session.mentee_left_at is not None:
                session.accounted_duration = session.mentee_left_at - session.started_at
                session.status_message = f'The lasted way more than it should, accounting duration based on the time where the mentee left the meeting {duration_to_str(session.accounted_duration)}.'
                return session
            else:
                session.accounted_duration = session.mentor.service.duration
                session.status_message = f'This session lasted more than a day, no one ever left, was probably never closed, accounting for standard duration {duration_to_str(session.accounted_duration)}.'
                return session

        session.accounted_duration = session.ended_at - session.started_at
        if session.accounted_duration > session.mentor.service.max_duration:
            if session.mentor.service.max_duration.seconds == 0:
                session.accounted_duration = session.mentor.service.duration
                session.status_message = f'No extra time is allowed for session, accounting for stantard duration of {duration_to_str(session.accounted_duration)}.'
                return session
            else:
                session.accounted_duration = session.mentor.service.max_duration
                session.status_message = f'The duration of the session is bigger than the maximun allowed, accounting for max duration of {duration_to_str(session.accounted_duration)}.'
                return session
        else:
            # everything perfect, we account for the expected
            return session

    else:
        session.accounted_duration = timedelta(seconds=0)
        session.status_message = f'No one joined this session, nothing will be accounted for.'
        return session


def generate_mentor_bill(mentor, reset=False):

    open_bill = MentorshipBill.objects.filter(mentor__id=mentor.id,
                                              academy__id=mentor.service.academy.id,
                                              status='DUE').first()
    if open_bill is None:
        open_bill = MentorshipBill(mentor=mentor, academy=mentor.service.academy)
        open_bill.save()

    unpaid_sessions = MentorshipSession.objects.filter(
        allow_billing=True, mentor__id=mentor.id, status__in=[
            'COMPLETED', 'FAILED'
        ]).filter(Q(bill__isnull=True) | Q(bill__status='DUE', bill__academy=mentor.service.academy))
    total = {'minutes': 0, 'overtime_minutes': 0}

    print('sessions found', unpaid_sessions.count())
    for session in unpaid_sessions:
        session.bill = open_bill

        # if reset=true all the sessions durations will be recalculated
        session = add_accounted_time(session, reset)

        extra_minutes = 0
        if session.accounted_duration > session.mentor.service.max_duration:
            session.accounted_duration = session.mentor.service.max_duration
            session.status_message += f' The session accounted duration was limited to the maximum allowed {duration_to_str(session.accounted_duration)}'

        if session.accounted_duration > session.mentor.service.duration:
            extra_minutes = (session.accounted_duration - session.mentor.service.duration).seconds / 60

        total['minutes'] = total['minutes'] + (session.accounted_duration.seconds / 60)
        total['overtime_minutes'] = total['overtime_minutes'] + extra_minutes

        session.save()

    total['hours'] = round(total['minutes'] / 60, 2)
    total['price'] = total['hours'] * mentor.price_per_hour

    open_bill.total_duration_in_hours = total['hours']
    open_bill.total_duration_in_minutes = total['minutes']
    open_bill.overtime_minutes = total['overtime_minutes']
    open_bill.total_price = total['price']
    open_bill.save()

    return open_bill
