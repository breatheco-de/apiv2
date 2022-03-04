import os, re, json, logging, time
from itertools import chain
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from breathecode.services.daily.client import DailyClient
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from .models import MentorshipSession
from .serializers import GETSessionReportSerializer

logger = logging.getLogger(__name__)
API_URL = os.getenv('API_URL', '')


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
            session.ends_at = timezone.now() + duration
            session.mentee = mentee
            session.save()
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


def extend_session(session, duration_in_minutes=30):

    # default duration can be ovveriden by service
    daily = DailyClient()
    room = daily.extend_room(name=session.name, exp_in_seconds=duration_in_minutes * 3600)

    session.ends_at = session.ends_at + timedelta(minutes=duration_in_minutes)
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
