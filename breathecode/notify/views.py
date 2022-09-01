import logging, re, os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import render
from django.utils import timezone
from rest_framework.permissions import AllowAny
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from breathecode.utils import (capable_of, GenerateLookupsMixin, ValidationException,
                               HeaderLimitOffsetPagination, APIViewExtensions)
from breathecode.admissions.models import Cohort, CohortUser, Academy
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy, Profile, CredentialsSlack
from .actions import get_template, get_template_content
from .models import Device, Hook
from .tasks import async_slack_action
from .serializers import DeviceSerializer, HookSerializer
from breathecode.services.slack.client import Slack
import traceback

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def preview_template(request, slug):
    template = get_template_content(slug, request.GET)
    return HttpResponse(template['html'])


@api_view(['GET'])
@permission_classes([AllowAny])
def preview_slack_template(request, slug):
    template = get_template_content(slug, request.GET, ['slack'])
    return HttpResponse(template['slack'])


@api_view(['GET'])
@permission_classes([AllowAny])
def test_email(request, email):
    # tags = sync_user_issues()
    # return Response(tags, status=status.HTTP_200_OK)
    pass


@api_view(['POST'])
@permission_classes([AllowAny])
def process_interaction(request):
    try:
        async_slack_action.delay(request.POST)
        logger.debug('Slack action enqueued')
        return Response(None, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception('Error processing slack action')
        return Response(str(e), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def slack_command(request):

    try:
        client = Slack()
        response = client.execute_command(context=request.data)
        logger.debug('Slack reponse')
        logger.debug(response)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:

        return Response(str(e), status=status.HTTP_200_OK)


class HooksView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort='-created_at', paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        items = Hook.objects.filter(user__id=request.user.id)
        lookup = {}

        start = request.GET.get('event', None)
        if start is not None:
            start_date = datetime.datetime.strptime(start, '%Y-%m-%d').date()
            lookup['created_at__gte'] = start_date

        if 'event' in self.request.GET:
            param = self.request.GET.get('event')
            lookup['event'] = param

        items = items.filter(**lookup)

        like = request.GET.get('like', None)
        if like is not None:
            items = items.filter(Q(event__icontains=like) | Q(target__icontains=like))

        items = handler.queryset(items)
        serializer = HookSerializer(items, many=True)

        return handler.response(serializer.data)

    def post(self, request):

        serializer = HookSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, hook_id):

        hook = Hook.objects.filter(id=hook_id, user__id=request.user.id).first()
        if hook is None:
            raise ValidationException(f'Hook {hook_id} not found for this user', slug='hook-not-found')

        serializer = HookSerializer(instance=hook, data=request.data, context={
            'request': request,
        })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, hook_id=None):

        filtered = False
        items = Hook.objects.filter(user__id=request.user.id)
        if hook_id is not None:
            items = items.filter(id=hook_id)
            filtered = True
        else:
            event = request.GET.get('event', None)
            if event is not None:
                filtered = True
                items = items.filter(event__in=event.split(','))

            service_id = request.GET.get('service_id', None)
            if service_id is not None:
                filtered = True
                items = items.filter(service_id__in=service_id.split(','))

        for item in items:
            item.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)
