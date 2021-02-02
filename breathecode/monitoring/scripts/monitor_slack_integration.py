#!/usr/bin/env python
"""
Alert me when something is missing with the Slack integration
"""
from breathecode.notify.models import SlackTeam
from breathecode.authenticate.models import CredentialsSlack
from django.db.models import Q

slack = SlackTeam.objects.filter(academy__id=academy.id).first()
if slack is None:
    result["details"] = "No slack integration has been found"
    result['status'] = "MINOR"
else:
    owner_credentials = CredentialsSlack.objects.filter(user__id=slack.owner.id).first()
    if owner_credentials is None:
        result["details"] = "The academy slack integration is not finished, the team owner needs to connect with slack"
        result['status'] = "MINOR"