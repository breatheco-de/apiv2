from django.shortcuts import render
from rest_framework.response import Response
from .serializers import PostFormEntrySerializer
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from .actions import register_new_lead, sync_tags, sync_automations
from .tasks import persist_single_lead

# Create your views here.
@api_view(['POST'])
@permission_classes([AllowAny])
def create_lead(request):
    serializer = PostFormEntrySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

        persist_single_lead.delay(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
@api_view(['GET'])
def sync_tags_with_active_campaign(request):
    tags = sync_tags()
    return Response(tags, status=status.HTTP_200_OK)

# Create your views here.
@api_view(['GET'])
def sync_automations_with_active_campaign(request):
    tags = sync_automations()
    return Response(tags, status=status.HTTP_200_OK)