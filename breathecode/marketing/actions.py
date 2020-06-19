import os, re
from itertools import chain
from .models import FormEntry, Tag
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from activecampaign.client import Client
client = Client(os.getenv('ACTIVE_CAMPAIGN_URL'), os.getenv('ACTIVE_CAMPAIGN_KEY'))

acp_ids = {
    "strong": "49",
    "soft": "48",
    "newsletter_list": "3",

    "utm_url": "15",
    "utm_location": "18",
    "course": "2",
    "utm_language": "16",
    "utm_country": "19",
    "gclid": "26",
    "referral_key": "27",
}

def set_optional(contact, key, data):
    if key in data:
        contact["field["+acp_ids[key]+",0]"] = data[key]

    return contact

def get_lead_tags(form_entry):
    if 'tags' not in form_entry:
        raise ValidationError('You need to specify tags for this entry')
    else:
        _tags = form_entry['tags'].split(",")
        if len(_tags) == 0:
            raise ValidationError('The contact tags are empty')
    
    strong_tags = Tag.objects.filter(slug__in=_tags, tag_type='STRONG')
    soft_tags = Tag.objects.filter(slug__in=_tags, tag_type='SOFT')
    dicovery_tags = Tag.objects.filter(slug__in=_tags, tag_type='DISCOVERY')
    other_tags = Tag.objects.filter(slug__in=_tags, tag_type='OTHER')

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) == 0:
        raise ValidationError('Tag applied to the contact not found')

    return tags

    
def register_new_lead(form_entry=None):
    print("form entry", form_entry)
    if form_entry is None:
        raise ValidationError('You need to specify the form entry data')

    tags = get_lead_tags(form_entry)
    print("found tags", tags)
    LEAD_TYPE = tags[0].tag_type
    automation = None
    if LEAD_TYPE.lower() in acp_ids:
        automation = acp_ids[LEAD_TYPE.lower()]

    contact = {
        "email": form_entry["email"],
        "firstName": form_entry["first_name"],
        "lastName": form_entry["last_name"],
        "phone": form_entry["phone"]
    }
    contact = set_optional(contact, 'utm_url', form_entry)
    contact = set_optional(contact, 'utm_location', form_entry)
    contact = set_optional(contact, 'course', form_entry)
    contact = set_optional(contact, 'utm_language', form_entry)
    contact = set_optional(contact, 'gclid', form_entry)
    contact = set_optional(contact, 'referral_key', form_entry)

    response = client.contacts.create_or_update_contact({ "contact": contact })
    contact_id = response['contact']['id']
    if 'contact' not in response:
        print("error adding contact", response)
        raise APIException('Could not save contact in CRM')

    if automation:
        data = {
            "contactAutomation": {
                "contact": contact_id,
                "automation": automation
            }
        }
        response = client.contacts.add_a_contact_to_an_automation(data)
        if 'contacts' not in response:
            print("error triggering atomation", response)
            raise APIException('Could add contact to Automation')

    for t in tags:
        data = {
            "contactTag": {
                "contact": contact_id,
                "tag": t.acp_id
            }
        }
        response = client.contacts.add_a_tag_to_contact(data)

    entry = FormEntry.objects.get(id=form_entry["id"])
    entry.storage_status = 'PERSISTED'
    entry.lead_type = tags[0].tag_type
    entry.save()

    form_entry['storage_status'] = 'PERSISTED'

    return form_entry

def sync_tags():
    response = client.tags.list_all_tags(limit=100)
    tags = response['tags']
    count = 0
    while len(response['tags']) == 100:
        count = count + 100
        response = client.tags.list_all_tags(limit=100,offset=count)
        tags = tags + response['tags']

    for tag in tags:
        t = Tag.objects.filter(acp_id=tag['id']).first()
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