from django.shortcuts import render
from django.utils import timezone
from .models import Application, Endpoint
from rest_framework.permissions import AllowAny
from .serializers import DeviceSerializer
from django.http import HttpResponseRedirect, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
# Create your views here.


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_endpoints(request):
    return Response([], status=status.HTTP_200_OK)


# Create your views here.
@api_view(['GET'])
@permission_classes([AllowAny])
def get_apps(request):
    return Response([], status=status.HTTP_200_OK)
