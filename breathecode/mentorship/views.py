from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from breathecode.admissions.models import Academy
from .models import MentorProfile, MentorshipService, MentorshipSession
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


def forward_booking_url(request, mentor_slug):
    mentor = MentorProfile.objects.filter(slug=mentor_slug)
    if mentor is None:
        raise ValidationException(f'No mentor with slug {slug}')

    return redirect(mentor.booking_url)


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
