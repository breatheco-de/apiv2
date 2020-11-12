from django.core.mail import EmailMultiAlternatives
from rest_framework.exceptions import APIException
import os, logging, json
from django.template.loader import get_template
from django.contrib.auth.models import User
from django.template import Context
from django.utils import timezone
from pyfcm import FCMNotification
from breathecode.authenticate.models import CredentialsSlack
from breathecode.services.slack import client
from breathecode.admissions.models import Cohort, CohortUser
from .models import Device, SlackChannel, SlackTeam, SlackUser, SlackUserTeam
from django.conf import settings
import requests
from twilio.rest import Client

push_service = None
FIREBASE_KEY = os.getenv('FIREBASE_KEY', None)
if FIREBASE_KEY is not None and FIREBASE_KEY != '':
    push_service = FCMNotification(api_key=FIREBASE_KEY)

logger = logging.getLogger(__name__)

def send_email_message(template_slug, to, data={}):
    if os.getenv('EMAIL_NOTIFICATIONS_ENABLED', False) == 'TRUE':

        template = get_template_content(template_slug, data, ["email"])

        result = requests.post(
            f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages",
            auth=(
                "api",
                os.environ.get('MAILGUN_API_KEY', "")),
            data={
                "from": f"BreatheCode <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                "to": to,
                "subject": template['subject'],
                "text": template['text'],
                "html": template['html']})
        
        if result.status_code != 200:
            logger.error(f"Error sending email, mailgun status code: {str(result.status_code)}")
            logger.error(result.text)
        else:
            logger.debug('Email notification  '+template_slug+' sent')

        return result.status_code == 200
    else:
        logger.warning('Email not sent because EMAIL_NOTIFICATIONS_ENABLED != TRUE')
        return True

def send_sms(slug, phone_number, data={}):

    template = get_template_content(slug, data, ["sms"])
    # Your Account Sid and Auth Token from twilio.com/console
    # DANGER! This is insecure. See http://twil.io/secure
    TWILLIO_SID = os.environ.get('TWILLIO_SID')
    TWILLIO_SECRET = os.environ.get('TWILLIO_SECRET')
    client = Client(TWILLIO_SID, TWILLIO_SECRET)

    try:
        message = client.messages.create(
            body=template['sms'],
            from_='+15017122661',
            to='+1'+phone_number
        )
        return True
    except Exception:
        return False

# entity can be a cohort or a user
def send_slack(slug, slack_entity, data={}):

    template = get_template_content(slug, data, ["slack"])
    
    if slack_entity is None:
        raise Exception("No slack entity (user or cohort) was found or given")
    
    if slack_entity.team is None:
        raise Exception("The entity must belong to a slack team to receive notifications")
    
    if slack_entity.team.credentials is None:
        raise Exception(f"The slack team {slack_entity.team.name} has no valid credentials")

    logger.debug(f"Sending slack message to {str(slack_entity)}")

    try:
        payload = json.loads(template['slack'])
        if "blocks" in payload:
            payload = payload["blocks"]

        api = client.Slack(slack_entity.team.credentials.token)
        data = api.post("chat.postMessage", {
            "channel": slack_entity.slack_id,
            "blocks": payload,
            "parse": "full"
        })
        logger.debug(f"Notification to {str(slack_entity)} sent")
        return True
    except Exception:
        logger.exception(f"Error sending notification to {str(slack_entity)}")
        return False


def send_fcm(slug, registration_ids, data={}):
    if(len(registration_ids) > 0 and push_service):
        template = get_template_content(slug, data, ["email", "fms"])

        if 'fms' not in template:
            raise APIException(
                "The template " +
                slug +
                " does not seem to have a valid FMS version")

        message_title = template['subject']
        message_body = template['fms']
        if 'DATA' not in data:
            raise Exception("There is no data for the notification")
        message_data = data['DATA']

        result = push_service.notify_multiple_devices(
            registration_ids=registration_ids,
            message_title=message_title,
            message_body=message_body,
            data_message=message_data)

        # if(result["failure"] or not result["success"]):
        #     raise APIException("Problem sending the notification")

        return result
    else:
        return False


def send_fcm_notification(slug, user_id, data={}):
    device_set = Device.objects.filter(user=user_id)
    registration_ids = [device.registration_id for device in device_set]
    send_fcm(slug, registration_ids, data)

def notify_all(slug, user, data):
    
    send_email_message("nps", user.email, data)
    send_slack("nps", user.slackuser, data)


def get_template_content(slug, data={}, formats=None):
    #d = Context({ 'username': username })
    con = {
        'SUBJECT': 'No subject',
        'API_URL': os.environ.get('API_URL'),
        'COMPANY_NAME': 'BreatheCode',
        'COMPANY_LEGAL_NAME': 'BreatheCode LLC',
        'COMPANY_ADDRESS': '1801 SW 3rd Ave, Ste 100, Miami',
        'style__success': '#99ccff',
        'style__danger': '#ffcccc',
        'style__secondary': '#ededed',
    }
    z = con.copy()   # start with x's keys and values
    z.update(data)

    templates = {}
    if 'SUBJECT' in z:
        templates["SUBJECT"] = z['SUBJECT']
        templates["subject"] = z['SUBJECT']
    elif 'subject' in z:
        templates["SUBJECT"] = z['subject']
        templates["subject"] = z['subject']

    if formats is None or "email" in formats:
        plaintext = get_template( slug + '.txt')
        html = get_template(slug + '.html')
        templates["text"] = plaintext.render(z)
        templates["html"] = html.render(z)

    if formats is not None and "slack" in formats:
        fms = get_template(slug + '.slack')
        templates["slack"] = fms.render(z)

    if formats is not None and "fms" in formats:
        fms = get_template(slug + '.fms')
        templates["fms"] = fms.render(z)

    if formats is not None and "sms" in formats:
        sms = get_template(slug + '.sms')
        templates["sms"] = sms.render(z)

    return templates

def sync_slack_team_channel(team_id):

    logger.debug(f"Sync slack team {team_id}: looking for channels")

    team = SlackTeam.objects.filter(id=team_id).first()
    if team is None:
        raise Exception("Invalid team id: "+str(team_id))

    credentials = CredentialsSlack.objects.filter(team_id=team.slack_id).first()
    if credentials is None:
        raise Exception(f"No credentials found for this team {team_id}")

    # Starting to sync, I need to reset the status
    team.sync_status = 'INCOMPLETED'
    team.synqued_at = timezone.now()
    team.save()
    
    api = client.Slack(credentials.token)
    data = api.get("conversations.list", {
        "types": "public_channel,private_channel"
    })
    
    logger.debug(f"Found {str(len(data['channels']))} channels, starting to sync")
    for channel in data["channels"]:

        # only sync channels
        if channel["is_channel"] == False and channel['is_group'] == False and channel['is_general'] == False:
            continue
        
        # will raise exception if it fails
        sync_slack_channel(channel, team)
    
    # finished sync, status back to normal
    team.sync_status = 'COMPLETED'
    team.save()
    
    return True

def sync_slack_team_users(team_id):

    logger.debug(f"Sync slack team {team_id}: looking for users")

    team = SlackTeam.objects.filter(id=team_id).first()
    if team is None:
        raise Exception("Invalid team id: "+str(team_id))

    credentials = CredentialsSlack.objects.filter(team_id=team.slack_id).first()
    if credentials is None:
        raise Exception(f"No credentials found for this team {team_id}")

    # Starting to sync, I need to reset the status
    team.sync_status = 'INCOMPLETED'
    team.synqued_at = timezone.now()
    team.save()
    
    api = client.Slack(credentials.token)
    data = api.get("users.list")
    
    logger.debug(f"Found {str(len(data['members']))} members, starting to sync")
    for member in data["members"]:

        # ignore bots
        if member["is_bot"] or member["name"] == "slackbot":
            continue
        
        # will raise exception if it fails
        sync_slack_user(member, team)
    
    # finished sync, status back to normal
    team.sync_status = 'COMPLETED'
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
            slack_id = payload["id"],
        )
        slack_user.save()
        
        if "email" not in payload["profile"]:
            logger.fatal("User without email")
            logger.fatal(payload)
            raise Exception("Slack users are not coming with emails from the API")
        

    cohort_user = CohortUser.objects.filter(user__email=payload["profile"]["email"], cohort__academy__id=team.academy.id).first()
    if cohort_user is not None:
        user = cohort_user.user

    user_team = SlackUserTeam.objects.filter(slack_team=team, slack_user=slack_user).first()
    if user_team is None:
        logger.debug("Creating teamuser for "+str(team)+" -> "+str(slack_user))
        user_team = SlackUserTeam(
            slack_team=team,
            slack_user=slack_user,
        )
        
    if user is None:
        user_team.sync_status = 'INCOMPLETED'
        user_team.sync_message = "No user found on breathecode with this email"
    else:
        user_team.sync_status = 'COMPLETED'
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
    channel = None
    if slack_channel is None:
        
        cohort = Cohort.objects.filter(slug=payload["name_normalized"]).first()
        if cohort is None:
            logger.warning(f"Slack channel {payload['name_normalized']} has no corresponding cohort in breathecode")

        slack_channel = SlackChannel(
            slack_id = payload["id"],
            team = team,
            sync_status = 'INCOMPLETED',
            cohort = cohort,
        )

    slack_channel.name = payload["name_normalized"]
    slack_channel.topic = payload["topic"]
    slack_channel.purpose = payload["purpose"]

    slack_channel.synqued_at = timezone.now()
    slack_channel.sync_status = 'COMPLETED'
    slack_channel.save()

    return slack_channel