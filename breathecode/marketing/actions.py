import os, re
from itertools import chain
from .models import FormEntry, Tag, Automation
from schema import Schema, And, Use, Optional, SchemaError
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from activecampaign.client import Client
client = Client(os.getenv('ACTIVE_CAMPAIGN_URL'), os.getenv('ACTIVE_CAMPAIGN_KEY'))

acp_ids = {
    # "strong": "49",
    # "soft": "48",
    # "newsletter_list": "3",

    "utm_url": "15",
    "utm_location": "18",
    "course": "2",
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
        raise ValidationError('You need to specify tags for this entry')
    else:
        _tags = form_entry['tags'].split(",")
        if len(_tags) == 0 or _tags[0] == '':
            raise ValidationError('The contact tags are empty', 400)
    
    strong_tags = Tag.objects.filter(slug__in=_tags, tag_type='STRONG')
    soft_tags = Tag.objects.filter(slug__in=_tags, tag_type='SOFT')
    dicovery_tags = Tag.objects.filter(slug__in=_tags, tag_type='DISCOVERY')
    other_tags = Tag.objects.filter(slug__in=_tags, tag_type='OTHER')

    tags = list(chain(strong_tags, soft_tags, dicovery_tags, other_tags))
    if len(tags) == 0:
        print("Tag applied to the contact not found or has tag_type assigned",_tags)
        raise ValidationError('Tag applied to the contact not found')

    return tags

def get_lead_automations(form_entry):
    _automations = []
    if 'automations' not in form_entry or form_entry['automations'] == '':
        return []
    else:
        _automations = form_entry['automations'].split(",")
    print("Base automations", _automations)
    
    automations = Automation.objects.filter(slug__in=_automations)
    print(f"found {str(automations.count())} automations")
    return automations.values_list('acp_id', flat=True)

    
def register_new_lead(form_entry=None):
    print("form entry", form_entry)
    if form_entry is None:
        raise ValidationError('You need to specify the form entry data')

    automations = get_lead_automations(form_entry)
    print("found automations", automations)

    tags = get_lead_tags(form_entry)
    print("found tags", tags)
    LEAD_TYPE = tags[0].tag_type
    if (automations is None or len(automations) == 0) and len(tags) > 0:
        automations = [tags[0].automation.acp_id]

    contact = {
        "email": form_entry["email"],
        "firstName": form_entry["first_name"],
        "lastName": form_entry["last_name"],
        "phone": form_entry["phone"]
    }
    contact = set_optional(contact, 'utm_url', form_entry)
    contact = set_optional(contact, 'utm_location', form_entry, "location")
    contact = set_optional(contact, 'course', form_entry)
    contact = set_optional(contact, 'utm_language', form_entry)
    contact = set_optional(contact, 'gclid', form_entry)
    contact = set_optional(contact, 'referral_key', form_entry)

    print("ready to send contact with following details: ", contact)
    response = client.contacts.create_or_update_contact({ "contact": contact })
    contact_id = response['contact']['id']
    if 'contact' not in response:
        print("error adding contact", response)
        raise APIException('Could not save contact in CRM')

    entry = FormEntry.objects.get(id=form_entry['id'])
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