from django.shortcuts import render
from rest_framework.response import Response
from .serializers import PostFormEntrySerializer
from rest_framework import status
from rest_framework.decorators import api_view
from .actions import register_new_lead, sync_tags

# Create your views here.
@api_view(['POST'])
def create_lead(request):
    serializer = PostFormEntrySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

        form_entry = register_new_lead(serializer.data)

        return Response(form_entry, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
@api_view(['GET'])
def sync_tags_with_active_campaign(request):
    tags = sync_tags()
    return Response(tags, status=status.HTTP_200_OK)