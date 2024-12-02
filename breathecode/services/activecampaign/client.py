import json
import logging
import os

import requests
from activecampaign.client import Client
from django.utils import timezone
from rest_framework.exceptions import APIException
from slugify import slugify

import breathecode.services.activecampaign.actions as actions

logger = logging.getLogger(__name__)

acp_ids = {
    # "strong": "49",
    # "soft": "48",
    # "newsletter_list": "3",
    "utm_plan": "67",
    "utm_placement": "66",
    "utm_term": "65",
    "utm_source": "59",
    "utm_medium": "36",
    "utm_content": "35",
    "utm_url": "60",
    "utm_location": "18",
    "utm_campaign": "33",
    "gender": "45",
    "course": "2",
    "client_comments": "13",
    "current_download": "46",  # used in downloadables
    "utm_language": "16",
    "utm_country": "19",
    "gclid": "26",
    "referral_key": "27",
    "deal": {
        "expected_cohort": "10",
        "expected_cohort_date": "21",
        "utm_location": "16",
        "utm_course": "6",
        "utm_url": "5",
        "gclid": "4",
        "utm_campaign": "7",
        "utm_source": "8",
        "utm_medium": "9",
        "utm_content": "70",
        "Deal_Phone": "65",
        "utm_term": "22",
        "utm_placement": "23",
        "referral_key": "34",
        "scheudule": "35",
    },
}


def map_ids(contact_customfield_id):
    contact_to_deal = {
        "66": "23",
        "65": "22",
        "59": "8",
        "36": "9",
        "60": "5",  # utm_url
        "18": "16",
        "33": "7",
        # "2": "65",  # phone
        "26": "4",
        "27": "34",
        "35": "70",  # utm_content
    }

    if contact_customfield_id in contact_to_deal:
        return contact_to_deal[contact_customfield_id]

    return None


class ActiveCampaignClient(Client):

    def _request(self, method, endpoint, headers=None, **kwargs):
        _headers = {"Accept": "application/json", "Content-Type": "application/json", "Api-Token": self.api_key}
        if headers:
            _headers.update(headers)

        kwargs["timeout"] = 2

        return self._parse(requests.request(method, self.BASE_URL + endpoint, headers=_headers, **kwargs))


class ActiveCampaign:
    headers = {}

    def __init__(self, token=None, url=None):
        if token is None:
            token = os.getenv("ACTIVE_CAMPAIGN_KEY", "")

        if url is None:
            url = os.getenv("ACTIVE_CAMPAIGN_URL", "")

        self.host = url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def execute_action(self, webhook_id: int):
        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.marketing.models import ActiveCampaignWebhook

        # example = {
        #     'api_url': 'https://www.eventbriteapi.com/{api-endpoint-to-fetch-object-details}/',
        #     'config': {
        #         'user_id': '154764716258',
        #         'action': 'test',
        #         'webhook_id': '5630182',
        #         'endpoint_url': 'https://8000-ed64b782-cdd5-479d-af25-8889ba085657.ws-us03.gitpod.io/v1/events/eventbrite/webhook'
        #     }
        # }

        webhook = ActiveCampaignWebhook.objects.filter(id=webhook_id).first()

        if not webhook:
            raise Exception("Invalid webhook")

        if not webhook.webhook_type:
            raise Exception("Impossible to webhook_type")

        webhook.run_at = timezone.now()

        action = webhook.webhook_type
        logger.debug(f"Executing ActiveCampaign Webhook => {action}")
        if hasattr(actions, action):

            logger.debug("Action found")
            fn = getattr(actions, action)

            try:
                fn(self, webhook, json.loads(webhook.payload), acp_ids)
                logger.debug("Mark active campaign action as done")
                webhook.status = "DONE"
                webhook.status_text = "OK"
                webhook.save()

            except Exception as e:
                logger.debug("Mark active campaign action with error")

                webhook.status = "ERROR"
                webhook.status_text = str(e)
                webhook.save()

        else:
            message = f"ActiveCampaign Action `{action}` is not implemented"
            logger.debug(message)

            webhook.status = "ERROR"
            webhook.status_text = message
            webhook.save()

            raise Exception(message)

    @staticmethod
    def add_webhook_to_log(context: dict, academy_slug: str):
        """Add one incoming webhook request to log."""

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.marketing.models import ActiveCampaignAcademy, ActiveCampaignWebhook

        if not context or not len(context):
            return None

        ac_academy = ActiveCampaignAcademy.objects.filter(academy__slug=academy_slug).first()
        if ac_academy is None:
            logger.debug(f"ActiveCampaign academy {str(academy_slug)} not found")
            raise APIException(f"ActiveCampaign academy {str(academy_slug)} not found")

        webhook = ActiveCampaignWebhook()
        webhook.webhook_type = context["type"]
        webhook.initiated_by = context["initiated_by"]
        webhook.ac_academy = ac_academy
        webhook.status = "PENDING"
        webhook.payload = json.dumps(context)
        webhook.save()

        return webhook

    def get_deal(self, deal_id):
        # /api/3/deals/id
        # Api-Token
        resp = requests.get(f"{self.host}/api/3/deals/{deal_id}", headers={"Api-Token": self.token}, timeout=2)
        logger.debug(f"Get deal {self.host}/api/3/deals/{deal_id}", resp.status_code)
        return resp.json()

    def update_deal(self, id: str, fields: dict):
        import requests

        # The following are the fields that can be updated on the deal
        _allowed_fields = [
            "contact",
            "account",
            "description",
            "currency",
            "group",
            "owner",
            "percent",
            "stage",
            "status",
            "title",
            "value",
            "fields",
        ]
        _allowed_custom_ids = [x for x in acp_ids["deal"].values()]
        # {
        #   "deal": {
        #     "contact": "51",
        #     "account": "45",
        #     "description": "This deal is an important deal",
        #     "currency": "usd",
        #     "group": "1",
        #     "owner": "1",
        #     "percent": null,
        #     "stage": "1",
        #     "status": 0,
        #     "title": "AC Deal",
        #     "value": 45600,
        #     "fields": [
        #       {
        #         "customFieldId": 1,
        #         "fieldValue": "First field value"
        #       },
        #       {
        #         "customFieldId": 2,
        #         "fieldValue": "2008-01-20"
        #       },
        #       {
        #         "customFieldId": 3,
        #         "fieldValue": 8800,
        #         "fieldCurrency": "USD"
        #       }
        #     ]
        #   }
        # }
        _to_be_updated = {"fields": []}
        for field_key in fields:
            if field_key not in _allowed_fields:
                logger.error(f'Error updating deal `{id}`, field "{field_key}" does not exist on active campaign deals')
                raise Exception(f"Field {field_key} does not exist for active campaign deals")

            # include all non-custom fields on the payload to be updated
            if field_key != "fields":
                _to_be_updated[field_key] = acp_ids[field_key]

        # custom fields validation
        if "fields" in fields:
            for cf in fields["fields"]:
                if cf["customFieldId"] not in _allowed_custom_ids:
                    logger.error(
                        f'Error updating deal `{id}`, custom field with id "{cf["customFieldId"]}" does not exist'
                    )
                    raise Exception(
                        f'Custom field with id {cf["customFieldId"]} does not exist for active campaign deals'
                    )

            _to_be_updated["fields"] = fields["fields"].copy()

        body = {
            "deal": {
                **_to_be_updated,
            }
        }

        resp = requests.put(f"{self.host}/api/3/deals/{id}", headers={"Api-Token": self.token}, json=body, timeout=2)
        logger.info(f"Updating lead `{id}` on active campaign")

        if resp.status_code in [201, 200]:
            logger.info("Deal updated successfully")
            body = resp.json()

            if "deal" in body:
                return body["deal"]

            else:
                logger.error(f"Failed to update deal with id `{id}` because the structure of response was changed")
                raise Exception(f"Failed to update deal with id `{id}` because the structure of response was changed")

        else:
            logger.error(f"Error updating deal `{id}` with status={str(resp.status_code)}")

            error = resp.json()
            logger.error(error)

            raise Exception(f"Error updating deal with id `{id}` with status={str(resp.status_code)}")

    def get_contact_by_email(self, email):
        import requests

        # /api/3/deals/id
        # Api-Token
        resp = requests.get(
            f"{self.host}/api/3/contacts", headers={"Api-Token": self.token}, params={"email": email}, timeout=2
        )
        logger.debug(f"Get contact by email {self.host}/api/3/contacts {resp.status_code}")
        data = resp.json()
        if data and "contacts" in data and len(data["contacts"]) == 1:
            return data["contacts"][0]
        else:
            raise Exception(f"Problem fetching contact in activecampaign with email {email}")

    def get_contact(self, id: str):
        import requests

        # "contact": {
        #     "cdate": "2007-05-05T12:49:09-05:00",
        #     "email": "charlesReynolds@example.com",
        #     "phone": "",
        #     "firstName": "Charles",
        #     "lastName": "Reynolds",
        #     "orgid": "0",
        #     "segmentio_id": "",
        #     "bounced_hard": "0",
        #     "bounced_soft": "0",
        #     "bounced_date": null,
        #     "ip": "0",
        #     "ua": null,
        #     "hash": "",
        #     "socialdata_lastcheck": null,
        #     "email_local": "",
        #     "email_domain": "",
        #     "sentcnt": "0",
        #     "rating_tstamp": null,
        #     "gravatar": "0",
        #     "deleted": "0",
        #     "adate": null,
        #     "udate": null,
        #     "edate": null,
        #     "contactAutomations": [
        #     "1"
        #     ],
        #     "contactLists": [
        #     "1"
        #     ],
        #     "fieldValues": [
        #     "1"
        #     ],
        #     "geoIps": [
        #     "1"
        #     ],
        #     "deals": [
        #     "1"
        #     ],
        #     "accountContacts": [
        #     "1"
        #     ],
        #     "links": {},
        #     "id": "1",
        #     "organization": null
        # }
        resp = requests.get(f"{self.host}/api/3/contacts/{id}", headers={"Api-Token": self.token}, timeout=2)
        logger.debug(f"Get contact by eidmail {self.host}/api/3/contacts/{id} => status={resp.status_code}")
        data = resp.json()
        if data and "contact" in data:
            return data["contact"]
        else:
            raise Exception(f"Problem fetching contact in activecampaign with id {id}")

    def get_contact_customfields(self, id: str):

        # {
        #     "fieldValues": [
        #         {
        #             "contact": "5",
        #             "field": "1",
        #             "value": "United States",
        #             "cdate": "2021-05-12T14:19:38-05:00",
        #             "udate": "2021-05-12T14:54:57-05:00",
        #             "created_by": "0",
        #             "updated_by": "0",
        #             "links": {
        #                 "owner": "https://:account.api-us1.com/api/3/fieldValues/1/owner",
        #                 "field": "https://:account.api-us1.com/api/3/fieldValues/1/field"
        #             },
        #             "id": "1",
        #             "owner": "5"
        #         },
        #     ]
        # }
        import requests

        resp = requests.get(
            f"{self.host}/api/3/contacts/{id}/fieldValues", headers={"Api-Token": self.token}, timeout=2
        )
        logger.debug(
            f"Get contact field values {self.host}/api/3/contacts/{id}/fieldValues => status={resp.status_code}"
        )
        data = resp.json()
        if data and "fieldValues" in data:
            return data["fieldValues"]
        else:
            raise Exception(f"Problem fetching contact custom fields in activecampaign with id {id}")

    def get_deal_customfields(self, deal_id):
        # /api/3/deals/id
        # Api-Token
        resp = requests.get(
            f"{self.host}/api/3/deals/{deal_id}/dealCustomFieldData", headers={"Api-Token": self.token}, timeout=2
        )
        logger.debug(
            f"Get custom fields {self.host}/api/3/deals/{deal_id}/dealCustomFieldData with status {str(resp.status_code)}"
        )

        if resp.status_code == 200:
            data = resp.json()
            _reponse = {}
            for field in data["dealCustomFieldData"]:
                _reponse[str(field["customFieldId"])] = field["fieldValue"]
            return _reponse

        return None

    def add_tag_to_contact(self, contact_id: int, tag_id: int):
        import requests

        # /api/3/deals/id
        # Api-Token
        body = {"contactTag": {"contact": contact_id, "tag": tag_id}}
        headers = {
            "Api-Token": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        resp = requests.post(f"{self.host}/api/3/contactTags", headers=headers, json=body, timeout=2)
        logger.debug("Add tag to contact")

        # can return status 200 if the contact have has been tagged, this case is not a error
        if resp.status_code < 400:
            data = resp.json()
            if data and "contactTag" in data:
                return data["contactTag"]
            else:
                raise Exception("Bad response format from ActiveCampaign when adding a new tag to contact")
        else:
            logger.error(resp.json())
            raise Exception(f"Failed to add tag to contact {contact_id} with status={resp.status_code}")

    def create_tag(self, slug: str, description: str):
        import requests

        # /api/3/deals/id
        # Api-Token
        body = {"tag": {"tag": slugify(slug), "tagType": "contact", "description": description}}
        resp = requests.post(f"{self.host}/api/3/tags", headers={"Api-Token": self.token}, json=body, timeout=2)
        logger.info(f'Creating tag `{body["tag"]["tag"]}` on active campaign')

        if resp.status_code == 201:
            logger.info("Tag created successfully")
            body = resp.json()

            if "tag" in body:
                return body["tag"]

            else:
                logger.error(f"Failed to create tag `{slug}` because the structure of response was changed")
                raise Exception(f"Failed to create tag `{slug}` because the structure of response was changed")

        else:
            logger.error(f"Error creating tag `{slug}` with status={str(resp.status_code)}")

            error = resp.json()
            logger.error(error)

            raise Exception(f"Error creating tag `{slug}` with status={str(resp.status_code)}")

    def delete_tag(self, tag_id: str):
        import requests

        # /api/3/deals/id
        # Api-Token
        resp = requests.delete(
            f"{self.host}/api/3/tags/{tag_id}",
            headers={"Api-Token": self.token},
            timeout=2,
        )
        logger.debug(f"Deleting tag {str(tag_id)} on active campaign")

        if resp.status_code == 200 or resp.status_code == 404:
            logger.debug(f"Tag deleted successfully or not existent {str(resp.status_code)} /api/3/tag/{tag_id}")
            return True
        else:
            logger.error(f"Error deleting tag `{str(tag_id)}` with status={str(resp.status_code)}")
            error = resp.json()
            logger.error(error)
            raise Exception(f"Error deleting tag `{str(tag_id)}` with status={str(resp.status_code)}")


class Contacts(object):

    def __init__(self, client):
        self.client = client

    def create_contact(self, data):
        """
        :param data: A dictionary with the parameters.

        ```py
        data ={
            "email": String, Unique email
            "first_name": String, First name of the contact.
            "last_name": String, Last name of the contact."
            "phone": An String, Phone number of the contact. Example: '+1 312 201 0300"
            "orgname": String. Organization name (if doesn't exist, this will create a new organization)
                        - MUST HAVE CRM FEATURE FOR THIS"
            "tags": String. Tags for this contact (comma-separated). Example: "tag1, tag2, etc"
            "ip4": IP address of the contact. Example: '127.0.0.1' If not supplied, it will default to '127.0.0.1"
            "field": String. Custom field values. Example: field[345,0] = 'value'. In this example,
                    "345" is the field ID. Leave 0 as is"
            "p[123]": String. Assign to lists. List ID goes in brackets, as well as the value"
            "status": String, The status for each list the contact is added to. Examples: 1 = active, 2 = unsubscribed"
            "form": String. Optional subscription Form ID, to inherit those redirection settings. Example: 1001.
                    This will allow you to mimic adding the contact through a subscription form, where you can take advantage
                    of the redirection settings."
            "noresponder": String. Whether or not to set "do not send any future responders." Examples: 1 = yes, 0 = no."
            "sdate": String. Subscribe date for particular list - leave out to use current date/time.
                    Example: '2009-12-07 06:00:00' Be sure to pass the date/time as CST (Central Standard Time)."
            "instantresponders": String. Use only if status = 1. Whether or not to set "send instant responders."
                                Examples: 1 = yes, 0 = no."
            "lastmessage": String. Whether or not to set "send the last broadcast campaign." Examples: 1 = yes, 0 = no."
            }
        ```
        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")
        return self.client._post("contact_sync", data=data)

    def subscribe_contact(self, data):
        """
        :param data: A dictionary with the parameters.

        ```py
        data ={
                "email": String, Unique email
                "first_name": String, First name of the contact.
                "last_name": String, Last name of the contact."
                "phone": An String, Phone number of the contact. Example: '+1 312 201 0300"
                "orgname": String. Organization name (if doesn't exist, this will create a new organization)
                            - MUST HAVE CRM FEATURE FOR THIS"
                "tags": String. Tags for this contact (comma-separated). Example: "tag1, tag2, etc"
                "ip4": IP address of the contact. Example: '127.0.0.1' If not supplied, it will default to '127.0.0.1"
                "field": String. Custom field values. Example: field[345,0] = 'value'. In this example,
                        "345" is the field ID. Leave 0 as is"
                "p[123]": String. Assign to lists. List ID goes in brackets, as well as the value"
                "status[123]": String, The status for each list the contact is added to. Examples: 1 = active, 2 = unsubscribed"
                "form": String. Optional subscription Form ID, to inherit those redirection settings. Example: 1001.
                        This will allow you to mimic adding the contact through a subscription form, where you can take advantage
                        of the redirection settings."
                "noresponder": String. Whether or not to set "do not send any future responders." Examples: 1 = yes, 0 = no."
                "sdate": String. Subscribe date for particular list - leave out to use current date/time.
                        Example: '2009-12-07 06:00:00' Be sure to pass the date/time as CST (Central Standard Time)."
                "instantresponders": String. Use only if status = 1. Whether or not to set "send instant responders."
                                    Examples: 1 = yes, 0 = no."
                "lastmessage": String. Whether or not to set "send the last broadcast campaign." Examples: 1 = yes, 0 = no."
            }
        ```

        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")

        return self.client._post("contact_add", data=data)

    def edit_contact(self, data):
        """
        :param data: A dictionary with the parameters.

        ```py
        data ={
            "email": String, Unique email
            "first_name": String, First name of the contact.
            "last_name": String, Last name of the contact."
            "phone": An String, Phone number of the contact. Example: '+1 312 201 0300"
            "orgname": String. Organization name (if doesn't exist, this will create a new organization)
                        - MUST HAVE CRM FEATURE FOR THIS"
            "tags": String. Tags for this contact (comma-separated). Example: "tag1, tag2, etc"
            "ip4": IP address of the contact. Example: '127.0.0.1' If not supplied, it will default to '127.0.0.1"
            "field": String. Custom field values. Example: field[345,0] = 'value'. In this example,
                    "345" is the field ID. Leave 0 as is"
            "p[123]": String. Assign to lists. List ID goes in brackets, as well as the value"
            "status": String, The status for each list the contact is added to. Examples: 1 = active, 2 = unsubscribed"
            "form": String. Optional subscription Form ID, to inherit those redirection settings. Example: 1001.
                    This will allow you to mimic adding the contact through a subscription form, where you can take advantage
                    of the redirection settings."
            "noresponder": String. Whether or not to set "do not send any future responders." Examples: 1 = yes, 0 = no."
            "sdate": String. Subscribe date for particular list - leave out to use current date/time.
                    Example: '2009-12-07 06:00:00' Be sure to pass the date/time as CST (Central Standard Time)."
            "instantresponders": String. Use only if status = 1. Whether or not to set "send instant responders."
                                Examples: 1 = yes, 0 = no."
            "lastmessage": String. Whether or not to set "send the last broadcast campaign." Examples: 1 = yes, 0 = no."
            }
        ```

        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")
        return self.client._post("contact_edit", data=data)

    def view_contact_email(self, email):
        return self.client._get("contact_view_email", aditional_data=[("email", email)])

    def view_contact(self, id):
        return self.client._get("contact_view", aditional_data=[("id", id)])

    def delete_contact(self, id):
        return self.client._get("contact_delete", aditional_data=[("id", id)])


class ACOldClient(object):

    def __init__(self, url, apikey):

        if url is None:
            raise Exception("Invalid URL for active campaign API, have you setup your env variables?")

        self._base_url = f"https://{url}" if not url.startswith("http") else url
        self._apikey = apikey
        self.contacts = Contacts(self)

    def _get(self, action, aditional_data=None):
        return self._request("GET", action, aditional_data=aditional_data)

    def _post(self, action, data=None, aditional_data=None):
        return self._request("POST", action, data=data, aditional_data=aditional_data)

    def _delete(self, action):
        return self._request("DELETE", action)

    def _request(self, method, action, data=None, aditional_data=None):
        params = [
            ("api_action", action),
            ("api_key", self._apikey),
            ("api_output", "json"),
        ]
        if aditional_data is not None:
            for aditional in aditional_data:
                params.append(aditional)
        response = requests.request(method, self._base_url + "/admin/api.php", params=params, data=data, timeout=3)

        if response.status_code >= 200 and response.status_code < 400:
            data = response.json()
            return self._parse(data)
        else:
            raise Exception("Error when saving contact on AC")

    def _parse(self, response):
        if response["result_code"] == 1:
            return response
        else:
            raise Exception(response["result_message"])
