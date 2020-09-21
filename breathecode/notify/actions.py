from django.core.mail import EmailMultiAlternatives
from rest_framework.exceptions import APIException
import os
from django.template.loader import get_template
from django.template import Context
from pyfcm import FCMNotification
from .models import Device
from django.conf import settings
import requests
from twilio.rest import Client

push_service = None
FIREBASE_KEY = os.environ.get('FIREBASE_KEY')
if(FIREBASE_KEY and FIREBASE_KEY!=''):
    push_service = FCMNotification(api_key=FIREBASE_KEY)


def send_email_message(template_slug, to, data={}):
    if os.getenv('EMAIL_NOTIFICATIONS_ENABLED') == 'TRUE':
        template = get_template_content(template_slug, data, ["email"])
        print('Email notification '+template_slug+' sent')
        return requests.post(
            f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/messages",
            auth=(
                "api",
                os.environ.get('MAILGUN_API_KEY')),
            data={
                "from": f"BreatheCode <mailgun@{os.environ.get('MAILGUN_DOMAIN')}>",
                "to": to,
                "subject": template['subject'],
                "text": template['text'],
                "html": template['html']}).status_code == 200
    else:
        print('Email not sent because notifications are not enabled')
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
    device_set = FCMDevice.objects.filter(user=user_id)
    registration_ids = [device.registration_id for device in device_set]
    send_fcm(slug, registration_ids, data)


def get_template_content(slug, data={}, formats=None):
    #d = Context({ 'username': username })
    con = {
        'subject': 'No subject',
        'API_URL': os.environ.get('API_URL'),
        'COMPANY_NAME': 'BreatheCode',
        'COMPANY_LEGAL_NAME': 'BreatheCode LLC',
        'COMPANY_ADDRESS': '1801 SW 3rd Ave, Ste 100, Miami'
    }
    z = con.copy()   # start with x's keys and values
    z.update(data)

    templates = {
        "subject": z['subject']
    }

    if formats is None or "email" in formats:
        plaintext = get_template( slug + '.txt')
        html = get_template(slug + '.html')
        templates["text"] = plaintext.render(z)
        templates["html"] = html.render(z)

    if formats is not None and "fms" in formats:
        fms = get_template(slug + '.fms')
        templates["fms"] = fms.render(z)

    if formats is not None and "sms" in formats:
        sms = get_template(slug + '.sms')
        templates["sms"] = sms.render(z)

    return templates