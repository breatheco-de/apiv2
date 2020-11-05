import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import render
from django.utils import timezone
from rest_framework.permissions import AllowAny
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from breathecode.admissions.models import Cohort
from .actions import get_template, get_template_content
from .models import Device
from .serializers import DeviceSerializer

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Cohort)
def post_save_cohort(sender, **kwargs):
    
    instance = kwargs["instance"]
    logger.debug("New cohort was saved")
    logger.debug(instance)


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def preview_template(request, slug):
    template = get_template_content(slug, request.GET)
    return HttpResponse(template['html'])

# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def test_email(request, email):
    # tags = sync_user_issues()
    # return Response(tags, status=status.HTTP_200_OK)
    pass