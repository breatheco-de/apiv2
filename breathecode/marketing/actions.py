import os, re, requests, logging
from itertools import chain
from django.utils import timezone
from .models import FormEntry, Tag, Automation, ActiveCampaignAcademy, AcademyAlias
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from activecampaign.client import Client
from rest_framework.decorators import api_view, permission_classes
from .serializers import FormEntrySerializer
from breathecode.notify.actions import send_email_message
from breathecode.authenticate.models import CredentialsFacebook
from breathecode.services.activecampaign import AC_Old_Client

logger = logging.getLogger(__name__)

SAVE_LEADS = os.getenv('SAVE_LEADS', None)
GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY', None)

acp_ids = {
    # "strong": "49",
    # "soft": "48",
    # "newsletter_list": "3",
    "utm_source": "34",
    "utm_url": "15",
    "utm_location": "18",
    "course": "2",
    "client_comments": "13",
    "utm_language": "16",
    "utm_country": "19",
    "gclid": "26",
    "referral_key": "27",
    "utm_campaign": "33",
}


def set_optional(contact, key, data, custom_key=None):
    if custom_key is None:
        custom_key = key

    if custom_key in data:
        contact["field[" + acp_ids[key] + ",0]"] = data[custom_key]

    return contact


def get_lead_tags(ac_academy, form_entry):
    if 'tags' not in form_entry or form_entry['tags'] == '':
        raise Exception('You need to specify tags for this entry')
    else:
        _tags = form_entry['tags'].split(",")
        if len(_tags) == 0 or _tags[0] == '':
            raise Exception('The contact tags are empty', 400)

    strong_tags = Tag.objects.filter(slug__in=_tags,
                                     tag_type='STRONG',
                                     ac_academy=ac_academy)
    soft_tags = Tag.objects.filter(slug__in=_tags,
                                   tag_type='SOFT',
                                   ac_academy=ac_academy)
    dicovery_tags = Tag.objects.filter(slug__in=_tags,
                                       tag_type='DISCOVERY',
                                       ac_academy=ac_academy)
    other_tags = Tag.objects.filter(slug__in=_tags,
                                    tag_type='OTHER',
                                    ac_academy=ac_academy)

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) == 0:
        logger.error(
            "Tag applied to the contact not found or has tag_type assigned")
        logger.error(_tags)
        raise Exception(
            'Tag applied to the contact not found or has not tag_type assigned'
        )

    return tags


def get_lead_automations(ac_academy, form_entry):
    _automations = []
    if 'automations' not in form_entry or form_entry['automations'] == '':
        return []
    else:
        _automations = form_entry['automations'].split(",")

    automations = Automation.objects.filter(slug__in=_automations,
                                            ac_academy=ac_academy)
    count = automations.count()
    if count == 0:
        _name = form_entry['automations']
        raise Exception(
            f"The specified automation {_name} was not found for this AC Academy"
        )

    logger.debug(f"found {str(count)} automations")
    return automations.values_list('acp_id', flat=True)


def add_to_active_campaign(contact, academy_id: int, automation_id: int):
    if not ActiveCampaignAcademy.objects.filter(
            academy__id=academy_id).count():
        raise Exception(f"No academy found with id {academy_id}")

    active_campaign_academy_values = [
        'ac_url', 'ac_key', 'event_attendancy_automation__id'
    ]
    ac_url, ac_key, event_attendancy_automation_id = ActiveCampaignAcademy.objects.filter(
        academy__id=academy_id).values_list(
            *active_campaign_academy_values).first()

    logger.debug("ready to send contact with following details")
    logger.debug(contact)

    old_client = AC_Old_Client(ac_url, ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response['subscriber_id']

    if 'subscriber_id' not in response:
        logger.error("error adding contact", response)
        raise APIException('Could not save contact in CRM')

    client = Client(ac_url, ac_key)

    if event_attendancy_automation_id != automation_id:
        message = 'Automation doesn\'t exist for this AC Academy'
        logger.debug(message)
        raise Exception(message)

    acp_id = Automation.objects.filter(id=automation_id).values_list(
        'acp_id', flat=True).first()

    if not acp_id:
        message = 'Automation acp_id doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

    data = {
        "contactAutomation": {
            "contact": contact_id,
            "automation": acp_id,
        }
    }

    response = client.contacts.add_a_contact_to_an_automation(data)

    if 'contacts' not in response:
        logger.error(f"error triggering automation with id {str(acp_id)}",
                     response)
        raise APIException('Could not add contact to Automation')
    else:
        logger.debug(f"Triggered automation with id {str(acp_id)}", response)
        # auto = Automation.objects.filter(acp_id=acp_id, ac_academy=ac_academy).first()
        # # entry.automation_objects.add(auto)


def register_new_lead(form_entry=None):
    if form_entry is None:
        raise Exception('You need to specify the form entry data')

    if 'location' not in form_entry or form_entry['location'] is None:
        raise Exception('Missing location information')

    ac_academy = None
    alias = AcademyAlias.objects.filter(
        active_campaign_slug=form_entry['location']).first()
    if alias is not None and alias.academy.activecampaignacademy is not None:
        ac_academy = alias.academy.activecampaignacademy
    else:
        ac_academy = ActiveCampaignAcademy.objects.filter(
            academy__slug=form_entry['location']).first()
    if ac_academy is None:
        raise Exception(f"No academy found with slug {form_entry['location']}")

    automations = get_lead_automations(ac_academy, form_entry)

    if automations:
        logger.debug("found automations")
        logger.debug(automations)
    else:
        logger.debug("automations not found")

    tags = get_lead_tags(ac_academy, form_entry)
    logger.debug("found tags")
    logger.debug(set(t.slug for t in tags))
    LEAD_TYPE = tags[0].tag_type
    if (automations is None or len(automations) == 0) and len(tags) > 0:
        if tags[0].automation is None:
            raise Exception(
                'No automation was specified and the the specified tag has no automation either'
            )

        automations = [tags[0].automation.acp_id]

    if not 'email' in form_entry:
        raise Exception('The email doesn\'t exist')

    if not 'first_name' in form_entry:
        raise Exception('The first name doesn\'t exist')

    if not 'last_name' in form_entry:
        raise Exception('The last name doesn\'t exist')

    if not 'phone' in form_entry:
        raise Exception('The phone doesn\'t exist')

    if not 'id' in form_entry:
        raise Exception('The id doesn\'t exist')

    contact = {
        "email": form_entry["email"],
        "first_name": form_entry["first_name"],
        "last_name": form_entry["last_name"],
        "phone": form_entry["phone"]
    }
    contact = set_optional(contact, 'utm_url', form_entry)
    contact = set_optional(contact, 'utm_location', form_entry, "location")
    contact = set_optional(contact, 'course', form_entry)
    contact = set_optional(contact, 'utm_language', form_entry, "language")
    contact = set_optional(contact, 'utm_country', form_entry, "country")
    contact = set_optional(contact, 'client_comments', form_entry,
                           "client_comments")
    contact = set_optional(contact, 'gclid', form_entry)
    contact = set_optional(contact, 'referral_key', form_entry)

    entry = FormEntry.objects.filter(id=form_entry['id']).first()

    if not entry:
        raise Exception('FormEntry not found (id: ' + str(form_entry['id']) +
                        ')')

    # save geolocalization info
    # save_get_geolocal(entry, form_enty)

    if 'contact-us' == tags[0].slug:
        send_email_message(
            'new_contact',
            ac_academy.academy.marketing_email,
            {
                "subject":
                f"New contact from the website {form_entry['first_name']} {form_entry['last_name']}",
                "full_name":
                form_entry['first_name'] + " " + form_entry['last_name'],
                "client_comments":
                form_entry['client_comments'],
                "data": {
                    **form_entry
                },
                # "data": { **form_entry, **address },
            })

    # ENV Variable to fake lead storage
    if SAVE_LEADS == 'FALSE':
        logger.debug(
            "Ignoring leads because SAVE_LEADS is FALSE on the env variables")
        return form_entry

    logger.debug("ready to send contact with following details: ", contact)
    old_client = AC_Old_Client(ac_academy.ac_url, ac_academy.ac_key)
    response = old_client.contacts.create_contact(contact)
    contact_id = response['subscriber_id']

    # save contact_id from active campaign
    entry.ac_contact_id = contact_id
    entry.save()

    if 'subscriber_id' not in response:
        logger.error("error adding contact", response)
        raise APIException('Could not save contact in CRM')

    client = Client(ac_academy.ac_url, ac_academy.ac_key)
    if automations:
        for automation_id in automations:
            data = {
                "contactAutomation": {
                    "contact": contact_id,
                    "automation": automation_id
                }
            }
            response = client.contacts.add_a_contact_to_an_automation(data)
            if 'contacts' not in response:
                logger.error(
                    f"error triggering automation with id {str(automation_id)}",
                    response)
                raise APIException('Could not add contact to Automation')
            else:
                logger.debug(
                    f"Triggered automation with id {str(automation_id)}",
                    response)
                auto = Automation.objects.filter(
                    acp_id=automation_id, ac_academy=ac_academy).first()
                entry.automation_objects.add(auto)

    for t in tags:
        data = {"contactTag": {"contact": contact_id, "tag": t.acp_id}}
        response = client.contacts.add_a_tag_to_contact(data)
        if 'contacts' in response:
            entry.tag_objects.add(t.id)

    entry.storage_status = 'PERSISTED'
    entry.save()

    form_entry['storage_status'] = 'PERSISTED'

    return entry


def test_ac_connection(ac_academy):
    client = Client(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=1)
    return response


def sync_tags(ac_academy):

    client = Client(ac_academy.ac_url, ac_academy.ac_key)
    response = client.tags.list_all_tags(limit=100)

    if 'tags' not in response:
        logger.error("Invalid tags incoming from AC")
        return False

    tags = response['tags']
    count = 0
    while len(response['tags']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100, offset=count)
        tags = tags + response['tags']

    for tag in tags:
        t = Tag.objects.filter(slug=tag['tag'], ac_academy=ac_academy).first()
        if t is None:
            t = Tag(
                slug=tag['tag'],
                acp_id=tag['id'],
                ac_academy=ac_academy,
            )

        t.subscribers = tag['subscriber_count']
        t.save()

    return response


def sync_automations(ac_academy):

    client = Client(ac_academy.ac_url, ac_academy.ac_key)
    response = client.automations.list_all_automations(limit=100)

    if 'automations' not in response:
        print("Invalid automations incoming from AC")
        return False

    automations = response['automations']
    count = 0
    while len(response['automations']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100, offset=count)
        automations = automations + response['automations']

    for auto in automations:
        a = Automation.objects.filter(acp_id=auto['id'],
                                      ac_academy=ac_academy).first()
        if a is None:
            a = Automation(
                acp_id=auto['id'],
                ac_academy=ac_academy,
            )
        a.name = auto['name']
        a.entered = auto['entered']
        a.exited = auto['exited']
        a.status = auto['status']
        a.save()

    return response


def save_get_geolocal(contact, form_entry=None):

    if 'latitude' not in form_entry or 'longitude' not in form_entry:
        form_entry = contact.toFormData()
        if 'latitude' not in form_entry or 'longitude' not in form_entry:
            return False
        if form_entry['latitude'] == '' or form_entry[
                'longitude'] == '' or form_entry[
                    'latitude'] is None or form_entry['longitude'] is None:
            return False

    result = {}
    resp = requests.get(
        f"https://maps.googleapis.com/maps/api/geocode/json?latlng={form_entry['latitude']},{form_entry['longitude']}&key={GOOGLE_CLOUD_KEY}"
    )
    data = resp.json()
    if 'status' in data and data['status'] == 'INVALID_REQUEST':
        raise Exception(data['error_message'])

    if 'results' in data:
        for address in data['results']:
            for component in address['address_components']:
                if 'country' in component['types'] and 'country' not in result:
                    result['country'] = component['long_name']
                if 'locality' in component[
                        'types'] and 'locality' not in result:
                    result['locality'] = component['long_name']
                if 'route' in component['types'] and 'route' not in result:
                    result['route'] = component['long_name']
                if 'postal_code' in component[
                        'types'] and 'postal_code' not in result:
                    result['postal_code'] = component['long_name']

    if 'country' in result:
        contact.country = result['country']

    if 'locality' in result:
        contact.city = result['locality']

    if 'route' in result:
        contact.street_address = result['route']

    if 'postal_code' in result:
        contact.zip_code = result['postal_code']

    contact.save()

    return True


def get_facebook_lead_info(lead_id, academy_id=None):

    now = timezone.now()

    lead = FormEntry.objects.filter(lead_id=lead_id).first()
    if lead is None:
        raise APIException(f"Invalid lead id: {lead_id}")

    credential = CredentialsFacebook.objects.filter(
        academy__id=academy_id, expires_at__gte=now).first()
    if credential is None:
        raise APIException("No active facebook credentials to get the leads")

    params = {"access_token": credential.token}
    resp = requests.get(f'https://graph.facebook.com/v8.0/{lead_id}/',
                        params=params)
    if resp.status_code == 200:
        logger.debug("Facebook responded with 200")
        data = resp.json()
        if "field_data" in data:
            lead.utm_campaign == data["ad_id"]
            lead.utm_medium == data["ad_id"]
            lead.utm_source == 'facebook'
            for field in data["field_data"]:
                if field["name"] == "first_name" or field[
                        "name"] == "full_name":
                    lead.first_name == field["values"]
                elif field["name"] == "last_name":
                    lead.last_name == field["values"]
                elif field["name"] == "email":
                    lead.email == field["values"]
                elif field["name"] == "phone":
                    lead.phone == field["values"]
            lead.save()
        else:
            logger.fatal("No information about the lead")
    else:
        logger.fatal(
            "Imposible to connect to facebook API and retrieve lead information"
        )
