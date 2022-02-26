import os, hashlib, timeago
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from breathecode.admissions.models import Academy
from breathecode.authenticate.models import Token
from breathecode.utils.private_view import private_view, render_message
from .models import MentorProfile, MentorshipService, MentorshipSession
from .forms import CloseMentoringSessionForm
from .actions import close_mentoring_session, get_or_create_sessions, render_session
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (
    GETServiceSmallSerializer,
    GETSessionSmallSerializer,
    GETMentorSmallSerializer,
    MentorSerializer,
    MentorUpdateSerializer,
    SessionSerializer,
    ServiceSerializer,
    GETMentorBigSerializer,
    GETServiceBigSerializer,
    GETSessionBigSerializer,
    GETSessionReportSerializer,
)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from django.db.models import Q

API_URL = os.getenv('API_URL', '')


def set_query_parameter(url, param_name, param_value):
    """Given a URL, set or replace a query parameter and return the
    modified URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)
    print(new_query_string, 'new_query_string')

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


@private_view
def forward_booking_url(request, mentor_slug, token):
    now = timezone.now()
    if isinstance(token, HttpResponseRedirect):
        return token

    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    if mentor.status != 'ACTIVE':
        return render_message(request, f'This mentor is not active')

    booking_url = mentor.booking_url
    if '?' not in booking_url:
        booking_url += '?'

    return render(request, 'book_session.html', {
        'SUBJECT': 'Mentoring Session',
        'mentor': mentor,
        'mentee': token.user,
        'booking_url': booking_url,
    })


@private_view
def forward_meet_url(request, mentor_slug, token):
    now = timezone.now()
    if isinstance(token, HttpResponseRedirect):
        return token

    redirect = request.GET.get('redirect', None)
    extend = request.GET.get('extend', None)
    session_id = request.GET.get('session', None)

    session = None
    mentee = token.user
    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    if mentor.status != 'ACTIVE':
        return render_message(request, f'This mentor is not active at the moment')

    # if the mentor is joining the meeting
    if mentor.user.id == mentee.id:
        mentee = None
        # we don't know the mentee so we seach-for or create the sesison with the mentor only

    if session_id and session_id != 'new':
        session = MentorshipSession.objects.filter(id=session_id).first()
        if session is None:
            return render_message(request, f'Session with id {session_id} not found')
    elif session_id != 'new':
        sessions = get_or_create_sessions(mentor, mentee)
        if sessions.count() == 1:
            session = sessions.first()
        else:
            return render(
                request, 'pick_session.html', {
                    'SUBJECT':
                    'Mentoring Session',
                    'sessions':
                    GETSessionReportSerializer(sessions, many=True).data,
                    'baseUrl':
                    request.get_full_path(),
                    'MESSAGE':
                    f'<h1>Choose a mentoring session</h1> Many mentoring sessions were found, please the one you want to continue:',
                })

    if mentor.user.id == token.user.id:
        session.mentor_joined_at = now

    if session.status not in ['PENDING', 'STARTED']:
        return render_message(
            request,
            f'This mentoring session has ended',
        )

    if session.ends_at is not None and session.ends_at < now:
        if session.mentor.user.id != token.user.id:
            return render_message(
                request,
                f'The mentoring session expired {timeago.format(session.ends_at, now)}, ask the mentor to extend the session if you need more time.',
            )
        elif extend is None:
            extend_url = set_query_parameter(request.get_full_path(), 'extend', 'true')
            return render_message(
                request,
                f'The mentoring session expired {timeago.format(session.ends_at, now)}: You can <a href="{extend_url}">extend it for another 30 minutes</a> or end the session right now.',
                btn_label='End Session',
                btn_url='/mentor/session/' + str(session.id) + '?token=' + token.key,
                btn_target='_self')
        else:
            session.ends_at = now + timedelta(minutes=30)

    if session.mentee is None:
        session.save()
        return render_session(request, session, token=token)

    if redirect is not None:
        session.started_at = now
        session.status = 'STARTED'
        session.save()
        return render_session(request, session, token=token)

    if session.mentor.user.first_name is None or session.mentor.user.first_name == '':
        session.mentor.user.first_name = 'a mentor.'
    return render(
        request, 'message.html', {
            'SUBJECT':
            'Mentoring Session',
            'BUTTON':
            'Start Session',
            'BUTTON_TARGET':
            '_self',
            'LINK':
            set_query_parameter('?' + request.GET.urlencode(), 'redirect', 'true'),
            'MESSAGE':
            f'Hello {session.mentee.first_name }, you are about to start a {session.mentor.service.name} with: {session.mentor.user.first_name} {session.mentor.user.last_name}',
        })


@private_view
def end_mentoring_session(request, session_id, token):
    now = timezone.now()
    if request.method == 'POST':
        _dict = request.POST.copy()
        form = CloseMentoringSessionForm(_dict)

        token = Token.objects.filter(key=_dict['token']).first()
        if token is None or (token.expires_at is not None and token.expires_at < now):
            messages.error(request, f'Invalid or expired deliver token {_dict["token"]}')
            return render(request, 'form.html', {'form': form})

        session = MentorshipSession.objects.filter(id=_dict['session_id']).first()
        if session is None:
            messages.error(request, 'Invalid session id')
            return render(request, 'form.html', {'form': form})

        if form.is_valid():
            if close_mentoring_session(session=session, data=_dict):
                return render_message(
                    request,
                    f'The mentoring session has been closed successfully, you can close this window.')
            else:
                return render_message(request, f'There was a problem ending the mentoring session')

    elif request.method == 'GET':
        session = MentorshipSession.objects.filter(id=session_id).first()
        if session is None:
            return render_message(request, f'Invalid session id {str(session_id)}')

        # this GET request occurs when the mentor leaves the session
        session.mentor_left_at = now
        session.save()

        if session.mentee is None:
            session.status = 'FAILED'
            session.summary = 'This session expired without assigned mentee, it probably means the mentee never came. It will be marked as failed'
            session.save()
            return render_message(
                request,
                f'<h1>Mentoring Session Error</h1> This session expired without assigned mentee, it probably means the mentee never came. It will be marked as failed'
            )

        _dict = request.GET.copy()
        _dict['token'] = request.GET.get('token', None)
        _dict['status'] = 'COMPLETED'
        _dict['summary'] = session.summary
        _dict[
            'student_name'] = session.mentee.first_name + ' ' + session.mentee.last_name + ', ' + session.mentee.email
        _dict['session_id'] = session.id
        form = CloseMentoringSessionForm(_dict)
    return render(
        request, 'form.html', {
            'form': form,
            'disabled': session.status not in ['PENDING', 'STARTED'],
            'btn_lable': 'End Mentoring Session'
            if session.status in ['PENDING', 'STARTED'] else 'Mentoring session already ended',
            'intro': 'Please fill the following information to formally end the session',
            'title': 'End Mentoring Session'
        })


class ServiceView(APIView, HeaderLimitOffsetPagination):
    # """
    # List all snippets, or create a new snippet.
    # """
    # @capable_of('crud_service')
    # def post(self, request, academy_id=None):

    #     serializer = SurveySerializer(data=request.data,
    #                                   context={
    #                                       'request': request,
    #                                       'academy_id': academy_id
    #                                   })
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # """
    # List all snippets, or create a new snippet.
    # """

    # @capable_of('crud_service')
    # def put(self, request, survey_id=None, academy_id=None):
    #     if survey_id is None:
    #         raise ValidationException('Missing survey_id')

    #     survey = MentorService.objects.filter(id=survey_id).first()
    #     if survey is None:
    #         raise NotFound('This survey does not exist')

    #     serializer = SurveyPUTSerializer(survey,
    #                                      data=request.data,
    #                                      context={
    #                                          'request': request,
    #                                          'survey': survey_id,
    #                                          'academy_id': academy_id
    #                                      })
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_service')
    def get(self, request, service_id=None, academy_id=None):

        if service_id is not None:
            service = MentorshipService.objects.filter(id=service_id, academy__id=academy_id).first()
            if service is None:
                raise NotFound('This service does not exist on this academy')

            serializer = GETServiceBigSerializer(service)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipService.objects.filter(academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETServiceSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class MentorView(APIView, HeaderLimitOffsetPagination):
    # """
    # List all snippets, or create a new snippet.
    # """
    @capable_of('crud_mentor')
    def post(self, request, academy_id=None):

        utc_now = timezone.now()
        token = hashlib.sha1((str(request.data['slug']) + str(utc_now)).encode('UTF-8')).hexdigest()

        serializer = MentorSerializer(data={
            **request.data, 'token': token
        },
                                      context={
                                          'request': request,
                                          'academy_id': academy_id
                                      })

        if serializer.is_valid():
            mentor = serializer.save()

            _serializer = GETMentorBigSerializer(mentor, many=False)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # """
    # List all snippets, or create a new snippet.
    # """

    @capable_of('crud_mentor')
    def put(self, request, mentor_id=None, academy_id=None):

        if mentor_id is None:
            raise ValidationException('Missing mentor ID on the URL', 404)

        mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
        if mentor is None:
            raise ValidationException('This mentor does not exist for this academy', 404)

        serializer = MentorUpdateSerializer(mentor,
                                            data=request.data,
                                            context={
                                                'request': request,
                                                'academy_id': academy_id
                                            })
        if serializer.is_valid():
            mentor = serializer.save()
            _serializer = GETMentorBigSerializer(mentor)
            return Response(_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_mentor')
    def get(self, request, mentor_id=None, academy_id=None):

        if mentor_id is not None:
            mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
            if mentor is None:
                raise ValidationException('This mentor does not exist on this academy', code=404)

            serializer = GETMentorBigSerializer(mentor)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorProfile.objects.filter(service__academy__id=academy_id)
        lookup = {}

        if 'service' in self.request.GET:
            param = self.request.GET.get('service')
            lookup['service__slug'] = param

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETMentorSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)


class SessionView(APIView, HeaderLimitOffsetPagination):
    """
    List all snippets, or create a new snippet.
    """
    @capable_of('crud_mentorship_session')
    def post(self, request, academy_id=None):

        serializer = ServiceSerializer(data=request.data,
                                       context={
                                           'request': request,
                                           'academy_id': academy_id
                                       })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # """
    # List all snippets, or create a new snippet.
    # """

    # @capable_of('crud_service')
    # def put(self, request, survey_id=None, academy_id=None):
    #     if survey_id is None:
    #         raise ValidationException('Missing survey_id')

    #     survey = MentorService.objects.filter(id=survey_id).first()
    #     if survey is None:
    #         raise NotFound('This survey does not exist')

    #     serializer = SurveyPUTSerializer(survey,
    #                                      data=request.data,
    #                                      context={
    #                                          'request': request,
    #                                          'survey': survey_id,
    #                                          'academy_id': academy_id
    #                                      })
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @capable_of('read_mentorship_session')
    def get(self, request, session_id=None, academy_id=None):

        if session_id is not None:
            session = MentorshipSession.objects.filter(id=session_id,
                                                       mentor__service__academy__id=academy_id).first()
            if session is None:
                raise ValidationException('This session does not exist on this academy', code=404)

            serializer = SessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorshipSession.objects.filter(mentor__service__academy__id=academy_id)
        lookup = {}

        if 'status' in self.request.GET:
            param = self.request.GET.get('status')
            lookup['status'] = param

        mentor = request.GET.get('mentor', None)
        if mentor is not None:
            lookup['mentor__id__in'] = mentor.split(',')

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETSessionSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)
