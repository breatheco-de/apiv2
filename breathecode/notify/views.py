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
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy, Profile
from .actions import get_template, get_template_content
from .models import Device
from .serializers import DeviceSerializer
from breathecode.services.slack import Slack

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
def test_email(request, email):
    # tags = sync_user_issues()
    # return Response(tags, status=status.HTTP_200_OK)
    pass

@api_view(['GET'])
@permission_classes([AllowAny])
def process_interaction(request):
    # tags = sync_user_issues()
    # return Response(tags, status=status.HTTP_200_OK)
    pass

@api_view(['POST'])
@permission_classes([AllowAny])
def get_student_info(request):

    user_id = request.POST["user_id"]
    team_id = request.POST["team_id"]
    content = request.POST["text"]

    try:
        user = ProfileAcademy.objects.filter(user__slackuser__slack_id=user_id, academy__slackteam__slack_id=team_id).first()
        if user is None:
            raise Exception("You don't have permissions to query students on this team")

        slack = Slack()
        data = slack.parse_command(content)
        
        if len(data["users"]) == 0:
            raise Exception("No usernames found on the command")

        cohort_users = CohortUser.objects.filter(user__slackuser__slack_id=data["users"][0], role='STUDENT')
        user = cohort_users.first()
        if user is None:
            raise Exception(f"Student {str(data['users'][0])} not found on any cohort")

        user = user.user
        cohorts = [c.cohort for c in cohort_users]

        avatar_url = os.getenv("API_URL","") + "/static/img/avatar.png"
        github_username = "Undefined"
        phone = "Undefined"
        try:
            github_username = user.profile.github_username
            avatar_url = user.profile.avatar_url
            phone = user.profile.phone
        except Profile.DoesNotExist:
            pass

        def get_string(_s):
            if _s is None:
                return "Undefined"
            else:
                return _s

        response = {
            "blocks": []
        }
        response["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Student Name:* {user.first_name} {user.last_name}\n*Github*: {github_username}\n*Phone*: {phone}\n*Cohorts:*: {','.join([c.name for c in cohorts])}\n*Education Status:* {','.join([c.educational_status for c in cohort_users])}\n*Finantial Status:* {','.join([get_string(c.finantial_status) for c in cohort_users])}"
            },
            "accessory": {
                "type": "image",
                "image_url": avatar_url,
                "alt_text": f"{user.first_name} {user.last_name}"
            }
        })
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(str(e), status=status.HTTP_200_OK)
