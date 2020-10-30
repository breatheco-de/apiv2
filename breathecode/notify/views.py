from django.shortcuts import render
from django.utils import timezone
from .models import Device
from rest_framework.permissions import AllowAny
from .serializers import DeviceSerializer
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from .actions import get_template, get_template_content
# Create your views here.


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def test_email(request, email):
    tags = sync_user_issues()
    return Response(tags, status=status.HTTP_200_OK)

# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def preview_template(request, slug):
    template = get_template_content(slug, request.GET)
    return HttpResponse(template['html'])