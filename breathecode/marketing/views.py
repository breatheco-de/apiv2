import os
from django.shortcuts import render
from rest_framework.response import Response
from .serializers import PostFormEntrySerializer
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from .actions import register_new_lead, sync_tags, sync_automations, get_facebook_lead_info
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
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def receive_facebook_lead(request):
    if request.method == 'GET':

        challenge = 'no challenge'
        if 'hub.challenge' in request.GET:
            challenge = request.GET['hub.challenge']
        
        verify_token = ''
        if 'hub.verify_token' in request.GET:
            verify_token = request.GET['hub.verify_token']

        mode = ''
        if 'hub.mode' in request.GET:
            mode = request.GET['hub.mode']

        if verify_token == os.getenv("FACEBOOK_VERIFY_TOKEN", ""):
            return Response(int(challenge), status=status.HTTP_200_OK)
        else:
            return Response(int(challenge), status=status.HTTP_400_BAD_REQUEST)
    else:
        print(request.data)
        if "object" in request.data:
            if request.data["object"] == "page":
                for entry in request.data["entry"]:
                    for changes in entry["changes"]:
                        if changes["field"] == "leadgen":
                            serializer = PostFormEntrySerializer(data={
                                "fb_leadgen_id": changes["value"]["leadgen_id"],
                                "fb_page_id": changes["value"]["page_id"],
                                "fb_form_id": changes["value"]["form_id"],
                                "fb_adgroup_id": changes["value"]["adgroup_id"],
                                "fb_ad_id": changes["value"]["ad_id"]
                            })
                            if serializer.is_valid():
                                serializer.save()
                                #persist_single_lead.delay(request.data)
                                return Response(serializer.data, status=status.HTTP_201_CREATED)
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response({"details": "No leads found"}, status=status.HTTP_400_BAD_REQUEST)



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