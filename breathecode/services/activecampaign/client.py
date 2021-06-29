import requests, json
from requests.auth import HTTPBasicAuth
import breathecode.services.activecampaign.actions as actions
import logging, re, os, json, inspect, urllib

logger = logging.getLogger(__name__)


class ActiveCampaign:
    headers = {}

    def __init__(self, token=None, url=None):
        if token is None:
            token = os.getenv('ACTIVE_CAMPAIGN_KEY', "")

        if url is None:
            url = os.getenv('ACTIVE_CAMPAIGN_URL', "")

        self.host = url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def execute_action(self, webhook_id: int):
        # wonderful way to fix one poor mocking system
        import requests

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
            raise Exception("Imposible to webhook_type")

        action = webhook.webhook_type
        logger.debug(f"Executing ActiveCampaign Webhook => {action}")
        if hasattr(actions, action):

            logger.debug("Action found")
            fn = getattr(actions, action)

            try:
                fn(self, webhook, json.loads(webhook.payload))
                logger.debug("Mark active campaign action as done")
                webhook.status = 'DONE'
                webhook.status_text = 'OK'
                webhook.save()

            except Exception as e:
                logger.debug("Mark active campaign action with error")

                webhook.status = 'ERROR'
                webhook.status_text = str(e)
                webhook.save()

        else:
            message = f"ActiveCampaign Action `{action}` is not implemented"
            logger.debug(message)

            webhook.status = 'ERROR'
            webhook.status_text = message
            webhook.save()

            raise Exception(message)

    @staticmethod
    def add_webhook_to_log(context: dict, academy_slug: str):
        """Add one incoming webhook request to log"""

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.marketing.models import ActiveCampaignWebhook, ActiveCampaignAcademy

        if not context or not len(context):
            return None

        ac_academy = ActiveCampaignAcademy.objects.filter(
            academy__slug=academy_slug).first()
        if ac_academy is None:
            logger.debug(
                f"ActiveCampaign academy {str(academy_slug)} not found")
            raise APIException(
                f"ActiveCampaign academy {str(academy_slug)} not found")

        webhook = ActiveCampaignWebhook()
        webhook.webhook_type = context['type']
        webhook.run_at = context['date_time']
        webhook.initiated_by = context['initiated_by']
        webhook.ac_academy = ac_academy
        webhook.status = 'PENDING'
        webhook.payload = json.dumps(context)
        webhook.save()

        return webhook


class Contacts(object):
    def __init__(self, client):
        self.client = client

    def create_contact(self, data):
        """
        :param data: A dictionary with the parameters
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
        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")
        return self.client._post("contact_sync", data=data)

    def subscribe_contact(self, data):
        """
        :param data: A dictionary with the parameters
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
        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")

        return self.client._post("contact_add", data=data)

    def edit_contact(self, data):
        """
        :param data: A dictionary with the parameters
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
        :return: A json
        """
        if "email" not in data:
            raise KeyError("The contact must have an email")
        return self.client._post("contact_edit", data=data)

    def view_contact_email(self, email):
        return self.client._get("contact_view_email",
                                aditional_data=[('email', email)])

    def view_contact(self, id):
        return self.client._get("contact_view", aditional_data=[('id', id)])

    def delete_contact(self, id):
        return self.client._get("contact_delete", aditional_data=[('id', id)])


class AC_Old_Client(object):
    def __init__(self, url, apikey):

        if url is None:
            raise Exception(
                "Invalid URL for active campaign API, have you setup your env variables?"
            )

        self._base_url = f"https://{url}" if not url.startswith(
            "http") else url
        self._apikey = apikey
        self.contacts = Contacts(self)
        # self.account = Account(self)
        # self.lists = Lists(self)
        # self.webhooks = Webhooks(self)
        # self.tasks = Tasks(self)
        # self.deals = Deals(self)
        # self.users = Users(self)

    def _get(self, action, aditional_data=None):
        return self._request('GET', action, aditional_data=aditional_data)

    def _post(self, action, data=None, aditional_data=None):
        return self._request('POST',
                             action,
                             data=data,
                             aditional_data=aditional_data)

    def _delete(self, action):
        return self._request('DELETE', action)

    def _request(self, method, action, data=None, aditional_data=None):
        params = [
            ('api_action', action),
            ('api_key', self._apikey),
            ('api_output', 'json'),
        ]
        if aditional_data is not None:
            for aditional in aditional_data:
                params.append(aditional)
        response = requests.request(method,
                                    self._base_url + "/admin/api.php",
                                    params=params,
                                    data=data)
        if response.status_code >= 200 and response.status_code < 400:
            data = response.json()
            return self._parse(data)
        else:
            print("Error when saving contact on AC", response.text)
            raise Exception("Error when saving contact on AC")

    def _parse(self, response):
        if response['result_code'] == 1:
            return response
        else:
            raise Exception(response["result_message"])
