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
from breathecode.utils import capable_of
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy, Profile, CredentialsSlack
from .actions import get_template, get_template_content
from .models import Device
from .tasks import async_slack_action
from .serializers import DeviceSerializer
from breathecode.services.slack.client import Slack

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Cohort)
def post_save_cohort(sender, **kwargs):

    instance = kwargs["instance"]
    logger.debug("New cohort was saved")
    logger.debug(instance)


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
        logger.debug("Slack action enqueued")
        return Response(None, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Error processing slack action")
        return Response(str(e), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def slack_command(request):

    try:
        client = Slack()
        response = client.execute_command(context=request.POST)
        logger.debug("Slack reponse")
        logger.debug(response)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(str(e), status=status.HTTP_200_OK)
