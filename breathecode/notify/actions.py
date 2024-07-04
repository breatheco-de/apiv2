import json
import logging
import os

import requests
from django.template.loader import get_template
from django.utils import timezone
from premailer import transform
from pyfcm import FCMNotification
from rest_framework.exceptions import APIException
from twilio.rest import Client

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.services.slack import client
from capyc.rest_framework.exceptions import ValidationException

from .models import Device, SlackChannel, SlackTeam, SlackUser, SlackUserTeam

push_service = None
FIREBASE_KEY = os.getenv("FIREBASE_KEY", None)
if FIREBASE_KEY is not None and FIREBASE_KEY != "":
    push_service = FCMNotification(api_key=FIREBASE_KEY)

logger = logging.getLogger(__name__)


def send_email_message(template_slug, to, data=None, force=False, inline_css=False, academy=None):

    if data is None:
        data = {}

    if to is None or to == "" or (isinstance(to, list) and len(to) == 0):
        raise ValidationException(f"Invalid email to send notification to {str(to)}")

    if isinstance(to, list) == False:
        to = [to]

    if os.getenv("EMAIL_NOTIFICATIONS_ENABLED", False) == "TRUE" or force:
        template = get_template_content(template_slug, data, ["email"], inline_css=inline_css, academy=academy)

        result = requests.post(
            f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages",
            auth=("api", os.environ.get("MAILGUN_API_KEY", "")),
            data={
                "from": f"4Geeks <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                "to": to,
                "subject": template["subject"],
                "text": template["text"],
                "html": template["html"],
            },
            timeout=2,
        )

        if result.status_code != 200:
            logger.error(f"Error sending email, mailgun status code: {str(result.status_code)}")
            logger.error(result.text)
        else:
            logger.debug("Email notification  " + template_slug + " sent")

        return result.status_code == 200
    else:
        logger.warning(f"Email to {to} not sent because EMAIL_NOTIFICATIONS_ENABLED != TRUE")
        return True


def send_sms(slug, phone_number, data=None, academy=None):

    if data is None:
        data = {}

    template = get_template_content(slug, data, ["sms"], academy=academy)
    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    twillio_sid = os.environ.get("TWILLIO_SID")
    twillio_secret = os.environ.get("TWILLIO_SECRET")
    client = Client(twillio_sid, twillio_secret)

    try:
        client.messages.create(body=template["sms"], from_="+15017122661", to="+1" + phone_number)
        return True
    except Exception:
        return False


# entity can be a cohort or a user
def send_slack(slug, slackuser=None, team=None, slackchannel=None, data=None, academy=None):

    if data is None:
        data = {}

    if academy:
        data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        data["COMPANY_LOGO"] = academy.logo_url
        data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            data["heading"] = academy.name

    remitent_id = None
    if slackuser is None and slackchannel is None:
        message = "No slack entity (user or cohort) was found or given"
        logger.error(message)
        raise Exception(message)

    credentials = None
    if team is not None and hasattr(team.owner, "credentialsslack"):
        credentials = team.owner.credentialsslack

    if slackuser is not None:
        remitent_id = slackuser.slack_id

    if slackchannel is not None:
        if remitent_id is None:
            remitent_id = slackchannel.slack_id

        if slackchannel.team is None:
            message = f"The slack channel {slackchannel.name} must belong to a slack team"
            logger.error(message)
            raise Exception(message)
        elif credentials is None:
            credentials = slackchannel.team.owner.credentialsslack

    if credentials:
        return send_slack_raw(slug, credentials.token, remitent_id, data)

    else:
        message = "Team owner not has slack credentials"
        logger.error(message)
        raise Exception(message)


# if would like to specify slack channel or user id and team
def send_slack_raw(slug, token, channel_id, data=None, academy=None):
    logger.debug(f"Sending slack message to {str(channel_id)}")

    if data is None:
        data = {}

    try:
        if "slack_payload" in data:
            payload = data["slack_payload"]
        else:
            template = get_template_content(slug, data, ["slack"], academy=academy)
            payload = json.loads(template["slack"])
            if "blocks" in payload:
                payload = payload["blocks"]

        # for modals mainly
        meta = ""
        if "private_metadata" in payload:
            meta = payload["private_metadata"]

        api = client.Slack(token)
        data = api.post(
            "chat.postMessage", {"channel": channel_id, "private_metadata": meta, "blocks": payload, "parse": "full"}
        )
        logger.debug(f"Notification to {str(channel_id)} sent")
        return True
    except Exception:
        logger.exception(f"Error sending notification to {str(channel_id)}")
        return False


def send_fcm(slug, registration_ids, data=None, academy=None):

    if data is None:
        data = {}

    if len(registration_ids) > 0 and push_service:
        template = get_template_content(slug, data, ["email", "fms"], academy=academy)

        if "fms" not in template:
            raise APIException("The template " + slug + " does not seem to have a valid FMS version")

        message_title = template["subject"]
        message_body = template["fms"]
        if "DATA" not in data:
            raise Exception("There is no data for the notification")
        message_data = data["DATA"]

        result = push_service.notify_multiple_devices(
            registration_ids=registration_ids,
            message_title=message_title,
            message_body=message_body,
            data_message=message_data,
        )

        # if(result["failure"] or not result["success"]):
        #     raise APIException("Problem sending the notification")

        return result
    else:
        return False


def send_fcm_notification(slug, user_id, data=None):

    if data is None:
        data = {}

    device_set = Device.objects.filter(user=user_id)
    registration_ids = [device.registration_id for device in device_set]
    send_fcm(slug, registration_ids, data)


def get_template_content(slug, data=None, formats=None, inline_css=False, academy=None):

    if data is None:
        data = {}

    # d = Context({ 'username': username })
    con = {
        "API_URL": os.environ.get("API_URL"),
        "COMPANY_NAME": os.environ.get("COMPANY_NAME", ""),
        "COMPANY_CONTACT_URL": os.environ.get("COMPANY_CONTACT_URL", ""),
        "COMPANY_LEGAL_NAME": os.environ.get("COMPANY_LEGAL_NAME", ""),
        "COMPANY_ADDRESS": os.environ.get("COMPANY_ADDRESS", ""),
        "style__success": "#99ccff",
        "style__danger": "#ffcccc",
        "style__secondary": "#ededed",
    }

    z = con.copy()  # start with x's keys and values
    z.update(data)

    templates = {}

    if academy:
        z["COMPANY_INFO_EMAIL"] = academy.feedback_email
        z["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        z["COMPANY_LOGO"] = academy.logo_url
        z["COMPANY_NAME"] = academy.name

        if "heading" not in z:
            z["heading"] = academy.name

    if formats is None or "email" in formats:
        if "SUBJECT" in z:
            templates["SUBJECT"] = z["SUBJECT"]
            templates["subject"] = z["SUBJECT"]
        elif "subject" in z:
            templates["SUBJECT"] = z["subject"]
            templates["subject"] = z["subject"]
        else:
            templates["SUBJECT"] = ("No subject specified",)
            templates["subject"] = "No subject specified"

        plaintext = get_template(slug + ".txt")
        html = get_template(slug + ".html")
        templates["text"] = plaintext.render(z)
        templates["html"] = html.render(z)

    if formats is not None and "html" in formats:
        html = get_template(slug + ".html")
        templates["html"] = html.render(z)

    if "html" in templates and inline_css:
        templates["html"] = transform(templates["html"])

    if formats is not None and "slack" in formats:
        fms = get_template(slug + ".slack")
        templates["slack"] = fms.render(z)

    if formats is not None and "fms" in formats:
        fms = get_template(slug + ".fms")
        templates["fms"] = fms.render(z)

    if formats is not None and "sms" in formats:
        sms = get_template(slug + ".sms")
        templates["sms"] = sms.render(z)

    return templates


def sync_slack_team_channel(team_id):
    from breathecode.authenticate.models import CredentialsSlack

    logger.debug(f"Sync slack team {team_id}: looking for channels")

    team = SlackTeam.objects.filter(id=team_id).first()
    if team is None:
        raise Exception("Invalid team id: " + str(team_id))

    credentials = CredentialsSlack.objects.filter(team_id=team.slack_id).first()
    if credentials is None or credentials.token is None:
        raise Exception(f"No credentials found for this team {team_id}")

    # Starting to sync, I need to reset the status
    team.sync_status = "INCOMPLETED"
    team.synqued_at = timezone.now()
    team.save()

    api = client.Slack(credentials.token)
    data = api.get(
        "conversations.list",
        {
            "types": "public_channel,private_channel",
            "limit": 300,
        },
    )

    channels = data["channels"]
    while (
        "response_metadata" in data
        and "next_cursor" in data["response_metadata"]
        and data["response_metadata"]["next_cursor"] != ""
    ):
        data = api.get(
            "conversations.list",
            {
                "limit": 300,
                "cursor": data["response_metadata"]["next_cursor"],
                "types": "public_channel,private_channel",
            },
        )
        channels = channels + data["channels"]

    logger.debug(f"Found {str(len(channels))} channels, starting to sync")
    for channel in channels:

        # only sync channels
        if channel["is_channel"] == False and channel["is_group"] == False and channel["is_general"] == False:
            continue

        # will raise exception if it fails
        sync_slack_channel(channel, team)

    # finished sync, status back to normal
    team.sync_status = "COMPLETED"
    team.save()

    return True


def sync_slack_team_users(team_id):
    from breathecode.authenticate.models import CredentialsSlack

    logger.debug(f"Sync slack team {team_id}: looking for users")

    team = SlackTeam.objects.filter(id=team_id).first()
    if team is None:
        raise Exception("Invalid team id: " + str(team_id))

    credentials = CredentialsSlack.objects.filter(team_id=team.slack_id).first()
    if credentials is None:
        raise Exception(f"No credentials found for this team {team_id}")

    # Starting to sync, I need to reset the status
    team.sync_status = "INCOMPLETED"
    team.synqued_at = timezone.now()
    team.save()

    api = client.Slack(credentials.token)
    data = api.get("users.list", {"limit": 300})

    members = data["members"]
    while (
        "response_metadata" in data
        and "next_cursor" in data["response_metadata"]
        and data["response_metadata"]["next_cursor"] != ""
    ):
        data = api.get("users.list", {"limit": 300, "cursor": data["response_metadata"]["next_cursor"]})
        members = members + data["members"]

    logger.debug(f"Found {str(len(members))} members, starting to sync")
    for member in members:

        # ignore bots
        if member["is_bot"] or member["name"] == "slackbot":
            continue

        # will raise exception if it fails
        sync_slack_user(member, team)

    # finished sync, status back to normal
    team.sync_status = "COMPLETED"
    team.save()

    return True


def sync_slack_user(payload, team=None):

    if team is None and "team_id" in payload:
        team = SlackTeam.objects.filter(id=payload["team_id"]).first()

    if team is None:
        raise Exception("Invalid or missing team")

    slack_user = SlackUser.objects.filter(slack_id=payload["id"]).first()
    user = None
    if slack_user is None:

        slack_user = SlackUser(
            slack_id=payload["id"],
        )
        slack_user.save()

        if "email" not in payload["profile"]:
            logger.fatal("User without email")
            logger.fatal(payload)
            raise Exception("Slack users are not coming with emails from the API")

    cohort_user = CohortUser.objects.filter(
        user__email=payload["profile"]["email"], cohort__academy__id=team.academy.id
    ).first()
    if cohort_user is not None:
        user = cohort_user.user
    else:
        logger.warning(
            f"Skipping user {payload['profile']['email']} because its not a member of any cohort in {team.academy.name}"
        )
        return False

    user_team = SlackUserTeam.objects.filter(slack_team=team, slack_user=slack_user).first()
    if user_team is None:
        user_team = SlackUserTeam(
            slack_team=team,
            slack_user=slack_user,
        )

    if user is None:
        user_team.sync_status = "INCOMPLETED"
        user_team.sync_message = "No user found on breathecode with this email"
    else:
        user_team.sync_status = "COMPLETED"
    user_team.save()

    slack_user.status_text = payload["profile"]["status_text"]
    slack_user.status_emoji = payload["profile"]["status_emoji"]

    if "real_name" in payload:
        slack_user.real_name = payload["real_name"]

    slack_user.display_name = payload["name"]
    slack_user.user = user
    slack_user.email = payload["profile"]["email"]
    slack_user.synqued_at = timezone.now()
    slack_user.save()

    return slack_user


def sync_slack_channel(payload, team=None):

    logger.debug(f"Synching channel {payload['name_normalized']}...")

    if team is None and "team_id" in payload:
        team = SlackTeam.objects.filter(id=payload["team_id"]).first()

    if team is None:
        raise Exception("Invalid or missing team")

    slack_channel = SlackChannel.objects.filter(slack_id=payload["id"]).first()
    if slack_channel is None:

        cohort = Cohort.objects.filter(slug=payload["name_normalized"]).first()
        if cohort is None:
            logger.warning(f"Slack channel {payload['name_normalized']} has no corresponding cohort in breathecode")

        slack_channel = SlackChannel(
            slack_id=payload["id"],
            team=team,
            sync_status="INCOMPLETED",
            cohort=cohort,
        )

    slack_channel.name = payload["name_normalized"]
    slack_channel.topic = payload["topic"]
    slack_channel.purpose = payload["purpose"]

    slack_channel.synqued_at = timezone.now()
    slack_channel.sync_status = "COMPLETED"
    slack_channel.save()

    return slack_channel
