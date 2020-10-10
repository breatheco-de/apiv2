import os, re, requests
from itertools import chain
from .models import FormEntry, Tag, Automation
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from activecampaign.client import Client
from .utils import AC_Old_Client
from breathecode.notify.actions import send_email_message

client = Client(os.getenv('ACTIVE_CAMPAIGN_URL'), os.getenv('ACTIVE_CAMPAIGN_KEY'))
old_client = AC_Old_Client(os.getenv('ACTIVE_CAMPAIGN_URL'), os.getenv('ACTIVE_CAMPAIGN_KEY'))
SAVE_LEADS = os.getenv('SAVE_LEADS',None)
GOOGLE_CLOUD_KEY = os.getenv('GOOGLE_CLOUD_KEY',None)

acp_ids = {
    # "strong": "49",
    # "soft": "48",
    # "newsletter_list": "3",

    "utm_url": "15",
    "utm_location": "18",
    "course": "2",
    "client_comments": "13",
    "utm_language": "16",
    "utm_country": "19",
    "gclid": "26",
    "referral_key": "27",
}

def set_optional(contact, key, data, custom_key=None):
    if custom_key is None:
        custom_key = key

    if custom_key in data:
        contact["field["+acp_ids[key]+",0]"] = data[custom_key]

    return contact

def get_lead_tags(form_entry):
    if 'tags' not in form_entry or form_entry['tags'] == '':
        raise Exception('You need to specify tags for this entry')
    else:
        _tags = form_entry['tags'].split(",")
        if len(_tags) == 0 or _tags[0] == '':
            raise Exception('The contact tags are empty', 400)
    
    strong_tags = Tag.objects.filter(slug__in=_tags, tag_type='STRONG')
    soft_tags = Tag.objects.filter(slug__in=_tags, tag_type='SOFT')
    dicovery_tags = Tag.objects.filter(slug__in=_tags, tag_type='DISCOVERY')
    other_tags = Tag.objects.filter(slug__in=_tags, tag_type='OTHER')

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) == 0:
        print("Tag applied to the contact not found or has tag_type assigned",_tags)
        raise Exception('Tag applied to the contact not found')

    return tags

def get_lead_automations(form_entry):
    _automations = []
    if 'automations' not in form_entry or form_entry['automations'] == '':
        return []
    else:
        _automations = form_entry['automations'].split(",")
    
    automations = Automation.objects.filter(slug__in=_automations)
    count = automations.count()
    if count == 0:
        _name = form_entry['automations']
        raise Exception(f"The specified automation {_name} was not found")
    
    print(f"found {str(count)} automations")
    return automations.values_list('acp_id', flat=True)

    
def register_new_lead(form_entry=None):
    print("form entry", form_entry)
    if form_entry is None:
        raise Exception('You need to specify the form entry data')

    automations = get_lead_automations(form_entry)
    print("found automations", automations)

    tags = get_lead_tags(form_entry)
    print("found tags", tags)
    LEAD_TYPE = tags[0].tag_type
    if (automations is None or len(automations) == 0) and len(tags) > 0:
        if tags[0].automation is None:
            raise Exception('No automation was specified and the the specified tag has no automation either')

        automations = [tags[0].automation.acp_id]

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
    contact = set_optional(contact, 'client_comments', form_entry, "client_comments")
    contact = set_optional(contact, 'gclid', form_entry)
    contact = set_optional(contact, 'referral_key', form_entry)

    entry = FormEntry.objects.get(id=form_entry['id'])
    
    # save geolocalization info
    # save_get_geolocal(entry, form_enty)

    if 'contact-us' == tags[0].slug:
        send_email_message('new_contact', 'info@4geeksacademy.com', { 
            "subject": f"New contact from the website {form_entry['first_name']} {form_entry['last_name']}", 
            "full_name": form_entry['first_name'] + " " + form_entry['last_name'],
            "client_comments": form_entry['client_comments'], 
            "data": { **form_entry },
            # "data": { **form_entry, **address },
        })

    # ENV Variable to fake lead storage
    if SAVE_LEADS == 'FALSE':
        print("Ignoring leads because SAVE_LEADS is FALSE on the env variables")
        return form_entry

    print("ready to send contact with following details: ", contact)
    response = old_client.contacts.create_contact(contact)
    contact_id = response['subscriber_id']
    if 'subscriber_id' not in response:
        print("error adding contact", response)
        raise APIException('Could not save contact in CRM')

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
                print(f"error triggering atomation with id {str(automation_id)}", response)
                raise APIException('Could not add contact to Automation')
            else:
                print(f"Triggered atomation with id {str(automation_id)}", response)
                auto = Automation.objects.get(acp_id=automation_id)
                entry.automation_objects.add(auto)

    for t in tags:
        data = {
            "contactTag": {
                "contact": contact_id,
                "tag": t.acp_id
            }
        }
        response = client.contacts.add_a_tag_to_contact(data)
        if 'contacts' in response:
            entry.tag_objects.add(t.id)


    entry.storage_status = 'PERSISTED'
    entry.save()

    form_entry['storage_status'] = 'PERSISTED'

    return entry

def sync_tags():
    response = client.tags.list_all_tags(limit=100)

    if 'tags' not in response:
        print("Invalid tags incoming from AC")
        return False

    tags = response['tags']
    count = 0
    while len(response['tags']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100,offset=count)
        tags = tags + response['tags']

    for tag in tags:
        t = Tag.objects.filter(slug=tag['tag']).first()
        if t is None:
            t = Tag(
                slug=tag['tag'],
                acp_id=tag['id'],
                subscribers=tag['subscriber_count'],
            )
        else:
            t.subscribers = tag['subscriber_count']
        t.save()

    return response

def sync_automations():
    response = client.automations.list_all_automations(limit=100)

    if 'automations' not in response:
        print("Invalid automations incoming from AC")
        return False
    # print(response)
    automations = response['automations']
    count = 0
    while len(response['automations']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100,offset=count)
        automations = automations + response['automations']

    for auto in automations:
        a = Automation.objects.filter(acp_id=auto['id']).first()
        if a is None:
            a = Automation(
                name=auto['name'],
                acp_id=auto['id'],
                entered=auto['entered'],
                exited=auto['exited'],
                status=auto['status'],
            )
        else:
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
        if form_entry['latitude'] == '' or form_entry['longitude'] == '' or form_entry['latitude'] is None or form_entry['longitude'] is None:
            return False

    result = {}
    resp = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?latlng={form_entry['latitude']},{form_entry['longitude']}&key={GOOGLE_CLOUD_KEY}")
    data = resp.json()
    if 'status' in data and data['status'] == 'INVALID_REQUEST':
        raise Exception(data['error_message'])

    if 'results' in data:
        for address in data['results']:
            for component in address['address_components']:
                if 'country' in component['types'] and 'country' not in result:
                    result['country'] = component['long_name']
                if 'locality' in component['types'] and 'locality' not in result:
                    result['locality'] = component['long_name']
                if 'route' in component['types'] and 'route' not in result:
                    result['route'] = component['long_name']
                if 'postal_code' in component['types'] and 'postal_code' not in result:
                    result['postal_code'] = component['long_name']


    contact.country = result['country']
    contact.city = result['locality']
    contact.street_address = result['route']
    contact.zip_code = result['postal_code']
    contact.save()
    
    return True

