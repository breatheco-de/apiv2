import os, re, json, logging, time, datetime, requests
from itertools import chain
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from breathecode.services.daily.client import DailyClient
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from .models import MentorshipSession, MentorshipBill
from breathecode.utils.datetime_interger import duration_to_str

logger = logging.getLogger(__name__)


def get_pending_sessions_or_create(token, mentor, mentee=None):

    # starting to pick pending sessions
    pending_sessions = []
    if mentee is not None:
        unfinished_with_mentee = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                                  mentee__id=mentee.id,
                                                                  status__in=['PENDING', 'STARTED'])
        if unfinished_with_mentee.count() > 0:
            pending_sessions += unfinished_with_mentee.values_list('pk', flat=True)

    # if its a mentor, I will force him to close pending sessions
    if mentor.user.id == token.user.id:
        unfinished_sessions = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                               status__in=['PENDING', 'STARTED'
                                                                           ]).exclude(id__in=pending_sessions)
        # if it has unishined meetings with already started
        if unfinished_sessions.count() > 0:
            pending_sessions += unfinished_sessions.values_list('pk', flat=True)

    # if its a mentee, and there are pending sessions without mentee assigned
    elif mentee is not None and mentee.id == token.user.id:
        unfinished_sessions = MentorshipSession.objects.filter(mentor__id=mentor.id,
                                                               mentee__isnull=True,
                                                               status__in=['PENDING'
                                                                           ]).order_by('-mentor_joined_at')

        if unfinished_sessions.count() > 0:
            # grab the last one the mentor joined
            last_one = unfinished_sessions.first()
            pending_sessions += [last_one.id]
            # close the rest
            close_mentoring_session(
                unfinished_sessions.exclude(id=last_one.id), {
                    'summary':
                    'Automatically closed, not enough information on the meeting the mentor forgot to specify the mentee and the mentee never joined',
                    'status': 'FAILED'
                })

    # return all the collected pending sessions
    if len(pending_sessions) > 0:
        return MentorshipSession.objects.filter(id__in=pending_sessions)

    # if force_create == True we will try getting from the available unnused sessions
    # if I'm here its because there was no previous pending sessions so we will create one

    # default duration can be overriden by service
    duration = timedelta(seconds=3600)
    if mentor.service.duration is not None:
        duration = mentor.service.duration

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
    from .serializers import GETSessionReportSerializer
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

    sessions_to_close = session
    if isinstance(session, MentorshipSession):
        sessions_to_close = MentorshipSession.objects.filter(id=session.id)

    sessions_to_close.update(summary=data['summary'], status=data['status'].upper(), ended_at=timezone.now())

    return sessions_to_close


def get_accounted_time(_session):
    def get_duration(session):
        response = {'accounted_duration': 0, 'status_message': ''}
        if session.started_at is None and session.mentor_joined_at is not None:
            response['status_message'] = 'Mentor joined but mentee never did, '
            if session.mentor.service.missed_meeting_duration.seconds > 0:
                response['accounted_duration'] = session.mentor.service.missed_meeting_duration
                response[
                    'status_message'] += f'{duration_to_str(response["accounted_duration"])} will be accounted for the bill.'
            else:
                response['accounted_duration'] = timedelta(seconds=0)
                response['status_message'] += f'No time will be included on the bill.'
            return response

        elif session.started_at is not None:

            if session.mentor_joined_at is None:
                response['accounted_duration'] = timedelta(seconds=0)
                response[
                    'status_message'] = 'The mentor never joined the meeting, no time will be accounted for.'
                return response

            if session.ended_at is None:
                if session.ends_at is not None and session.ends_at > session.started_at:
                    response['accounted_duration'] = session.ends_at - session.started_at
                    response[
                        'status_message'] = f'The session never ended, accounting for the expected meeting duration that was {duration_to_str(response["accounted_duration"])}.'
                    return response
                elif session.mentee_left_at is not None:
                    response['accounted_duration'] = session.mentee_left_at - session.started_at
                    response[
                        'status_message'] = f'The session never ended, accounting duration based on the time where the mentee left the meeting {duration_to_str(response["accounted_duration"])}.'
                    return response
                elif session.mentor_left_at is not None:
                    response['accounted_duration'] = session.mentor_left_at - session.started_at
                    response[
                        'status_message'] = f'The session never ended, accounting duration based on the time where the mentor left the meeting {duration_to_str(response["accounted_duration"])}.'
                    return response
                else:
                    response['accounted_duration'] = session.mentor.service.duration
                    response[
                        'status_message'] = f'The session never ended, accounting for the standard duration {duration_to_str(response["accounted_duration"])}.'
                    return response

            if session.started_at > session.ended_at:
                response['accounted_duration'] = timedelta(seconds=0)
                response[
                    'status_message'] = 'Meeting started before it ended? No duration will be accounted for.'
                return response

            if (session.ended_at - session.started_at).days > 1:
                if session.mentee_left_at is not None:
                    response['accounted_duration'] = session.mentee_left_at - session.started_at
                    response[
                        'status_message'] = f'The lasted way more than it should, accounting duration based on the time where the mentee left the meeting {duration_to_str(response["accounted_duration"])}.'
                    return response
                else:
                    response['accounted_duration'] = session.mentor.service.duration
                    response[
                        'status_message'] = f'This session lasted more than a day, no one ever left, was probably never closed, accounting for standard duration {duration_to_str(response["accounted_duration"])}.'
                    return response

            response['accounted_duration'] = session.ended_at - session.started_at
            if response['accounted_duration'] > session.mentor.service.max_duration:
                if session.mentor.service.max_duration.seconds == 0:
                    response['accounted_duration'] = session.mentor.service.duration
                    response[
                        'status_message'] = f'No extra time is allowed for session, accounting for stantard duration of {duration_to_str(response["accounted_duration"])}.'
                    return response
                else:
                    response['accounted_duration'] = session.mentor.service.max_duration
                    response[
                        'status_message'] = f'The duration of the session is bigger than the maximun allowed, accounting for max duration of {duration_to_str(response["accounted_duration"])}.'
                    return response
            else:
                # everything perfect, we account for the expected
                return response

        else:
            response['accounted_duration'] = timedelta(seconds=0)
            response['status_message'] = f'No one joined this session, nothing will be accounted for.'
            return response

    _duration = get_duration(_session)
    if _duration['accounted_duration'] > _session.mentor.service.max_duration:
        _duration['accounted_duration'] = session.mentor.service.max_duration
        _duration[
            'status_message'] += f' The session accounted duration was limited to the maximum allowed {duration_to_str(_duration["accounted_duration"])}'
    return _duration


def last_month_date(current_date):
    # getting next month
    # using replace to get to last day + offset
    # to reach next month
    nxt_mnth = current_date.replace(day=28, hour=23, minute=59, second=59) + datetime.timedelta(days=4)

    # subtracting the days from next month date to
    # get last date of current Month
    last_datetime = (nxt_mnth - datetime.timedelta(days=nxt_mnth.day))

    return last_datetime


def generate_mentor_bills(mentor, reset=False):

    generated_bills = []
    start_at = None
    end_at = None

    def get_unpaid_sessions():
        return MentorshipSession.objects.filter(
            allow_billing=True, mentor__id=mentor.id,
            status__in=['COMPLETED', 'FAILED']).filter(started_at__isnull=False).filter(
                Q(bill__isnull=True)
                | Q(bill__status='DUE', bill__academy=mentor.service.academy)).order_by('started_at')

    previous_bill = MentorshipBill.objects.filter(mentor__id=mentor.id,
                                                  academy__id=mentor.service.academy.id,
                                                  status='DUE').order_by('-started_at').first()

    if previous_bill is not None and previous_bill.ended_at > timezone.now():
        return generated_bills

    monthly_unpaid_sessions = None
    while end_at is None or end_at < timezone.now():

        unpaid_sessions = get_unpaid_sessions()
        #print("Sessions: " + "".join([str(s.started_at) for s in unpaid_sessions]))
        if unpaid_sessions.count() == 0:
            return generated_bills

        if previous_bill is None:
            start_at = unpaid_sessions.first().started_at
            end_at = last_month_date(start_at)
        else:
            start_at = previous_bill.ended_at + datetime.timedelta(seconds=1)
            end_at = last_month_date(start_at)
            # raise Exception(f"Starting from {start_at} to {end_at}")

        open_bill = MentorshipBill(mentor=mentor,
                                   academy=mentor.service.academy,
                                   started_at=start_at,
                                   ended_at=end_at)
        open_bill.save()

        monthly_unpaid_sessions = unpaid_sessions.filter(started_at__gte=start_at, started_at__lte=end_at)
        print(
            f'There are {len(monthly_unpaid_sessions)} unpaid sessions starting from {start_at} to {end_at}')
        total = {'minutes': 0, 'overtime_minutes': 0}

        for session in monthly_unpaid_sessions:
            session.bill = open_bill

            _result = get_accounted_time(session)
            session.suggested_accounted_duration = _result['accounted_duration']
            session.status_message = _result['status_message']
            # if is null and reset=true all the sessions durations will be rest to the suggested one
            if session.accounted_duration is None or reset == True:
                session.accounted_duration = _result['accounted_duration']

            extra_minutes = 0
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

        generated_bills.append(open_bill)
        print(f'Added bill with total ammount {open_bill.total_duration_in_hours}')

        # the recently created bill is not the previous because we moving on to the next cycle
        previous_bill = open_bill
        print(f'Billing until {end_at} vs {timezone.now()}')

    return generated_bills


def mentor_is_ready(mentor):

    if mentor.online_meeting_url is None or mentor.online_meeting_url == '':
        raise Exception(
            f'Mentor {mentor.name} does not have backup online_meeting_url, update the value before activating.'
        )
    elif mentor.booking_url is None or 'https://calendly.com' not in mentor.booking_url:
        raise Exception(
            f'Mentor {mentor.name} booking_url must point to calendly, update the value before activating.')
    elif len(mentor.syllabus.all()) == 0:
        raise Exception(
            f'Mentor {mentor.name} has no syllabus associated, update the value before activating.')
    else:
        response = requests.head(mentor.booking_url)
        if response.status_code > 399:
            raise Exception(
                f'Mentor {mentor.name} booking URL is failing with code {str(response.status_code)}')
        response = requests.head(mentor.online_meeting_url)
        if response.status_code > 399:
            raise Exception(
                f'Mentor {mentor.name} online_meeting_url is failing with code {str(response.status_code)}')

    return True
