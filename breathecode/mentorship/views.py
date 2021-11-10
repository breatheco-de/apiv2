import os
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit
from django.shortcuts import render
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from breathecode.admissions.models import Academy
from breathecode.authenticate.models import Token
from breathecode.utils.private_view import private_view, render_message
from .models import MentorProfile, MentorshipService, MentorshipSession
from .forms import CloseMentoringSessionForm
from .actions import close_mentoring_session
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (
    GETServiceSmallSerializer,
    GETSessionSmallSerializer,
    GETMentorSmallSerializer,
    MentorSerializer,
    SessionSerializer,
    ServiceSerializer,
    GETMentorBigSerializer,
    GETServiceBigSerializer,
)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from django.db.models import Q


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

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


@private_view
def forward_booking_url(request, mentor_slug, token):

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

    if isinstance(token, HttpResponseRedirect):
        return token

    redirect = request.GET.get('redirect', None)

    mentor = MentorProfile.objects.filter(slug=mentor_slug).first()
    if mentor is None:
        return render_message(request, f'No mentor found with slug {mentor_slug}')

    if mentor.status != 'ACTIVE':
        return render_message(request, f'This mentor is not active')

    session = MentorshipSession.objects.filter(mentor__slug=mentor_slug,
                                               mentee__id=token.user.id,
                                               status='PENDING').first()
    if session is None and redirect is not None:
        return render_message(
            request, f'No mentoring session found with {mentor.user.first_name} {mentor.user.last_name}')

    if session is None:
        session = MentorshipSession(mentor=mentor,
                                    mentee=token.user,
                                    is_online=True,
                                    online_meeting_url=mentor.online_meeting_url)
        session.save()
    elif redirect is not None:
        session.started_at = timezone.now()
        session.status = 'STARTED'
        session.save()
        return HttpResponseRedirect(redirect_to=session.online_meeting_url)

    return render(
        request, 'mentoring_session.html', {
            'SUBJECT': 'Mentoring Session',
            'meeting_url': set_query_parameter('?' + request.GET.urlencode(), 'redirect', 'true'),
            'session': session,
        })


@private_view
def end_mentoring_session(request, session_id, token):

    if request.method == 'POST':
        _dict = request.POST.copy()
        form = CloseMentoringSessionForm(_dict)

        token = Token.objects.filter(key=_dict['token']).first()
        if token is None or token.expires_at < timezone.now():
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

        _dict = request.GET.copy()
        _dict['token'] = request.GET.get('token', None)
        _dict['status'] = session.status
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

    @capable_of('read_mentorhip_service')
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

    @capable_of('read_mentorhip_mentor')
    def get(self, request, mentor_id=None, academy_id=None):

        if mentor_id is not None:
            mentor = MentorProfile.objects.filter(id=mentor_id, service__academy__id=academy_id).first()
            if mentor is None:
                raise ValidationException('This mentor does not exist on this academy', code=404)

            serializer = GETMentorBigSerializer(mentor)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = MentorProfile.objects.filter(service__academy__id=academy_id)
        lookup = {}

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

    @capable_of('read_mentorhip_session')
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

        items = items.filter(**lookup).order_by('-created_at')

        page = self.paginate_queryset(items, request)
        serializer = GETSessionSmallSerializer(page, many=True)

        if self.is_paginate(request):
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)
