import logging
import os
import urllib
from json import JSONDecodeError
from urllib.parse import urlparse
import breathecode.services.calendly.actions as actions
import traceback

logger = logging.getLogger(__name__)
API_URL = os.getenv("API_URL", "")


class Calendly:
    # HOST = "https://slack.com/api/"
    headers = {}

    def __init__(self, token):
        self.host = "https://api.calendly.com"
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def has_error(self):
        # {
        #     "error": "VENUE_AND_ONLINE",
        #     "error_description": "You cannot both specify a venue and set online_event",
        #     "status_code": 400
        # }
        pass

    def request(self, _type, url, headers=None, query_string=None, json=None):
        # wonderful way to fix one poor mocking system
        import requests

        if headers is None:
            headers = {}

        _headers = {**self.headers, **headers}
        _query_string = ""
        if query_string is not None:
            _query_string = "?" + urllib.parse.urlencode(query_string)

        if json is not None:
            response = requests.request(_type, self.host + url + _query_string, headers=_headers, timeout=2, json=json)
        else:
            response = requests.request(_type, self.host + url + _query_string, headers=_headers, timeout=2)

        result = None
        try:
            result = response.json()
        except JSONDecodeError as e:
            if _type != "DELETE":
                raise e

        if response.status_code >= 400:
            print("Error calling calendly: ", self.host + url + _query_string)
            raise Exception(result["message"])

        if result is not None and "pagination" in result:
            if result["pagination"]["next_page"] is not None:
                new_result = self.request(
                    _type,
                    result["pagination"]["next_page"],
                    query_string={
                        **query_string,
                    },
                )
                if "collection" in new_result and type(new_result["collection"]) == "list":
                    new_result["collection"] = result["collection"] + new_result["collection"]
                result.update(new_result)

        return result

    def subscribe(self, org_uri, org_hash):
        data = self.request(
            "POST",
            "/webhook_subscriptions",
            json={
                "url": f"{API_URL}/v1/mentorship/calendly/webhook/{org_hash}",
                "events": ["invitee.created", "invitee.canceled"],
                "organization": f"{org_uri}",
                "scope": "organization",
            },
        )
        if "collection" in data:
            return data["collection"]
        else:
            return data

    def unsubscribe(self, webhook_uuid):
        return self.request("DELETE", f"/webhook_subscriptions/{webhook_uuid}")

    def unsubscribe_all(self, org_uri):
        data = self.get_subscriptions(org_uri)
        for webhook in data:
            self.unsubscribe(urlparse(webhook["uri"]).path.split("/")[-1])

    def get_subscriptions(self, org_uri):
        data = self.request(
            "GET",
            "/webhook_subscriptions",
            query_string={
                "organization": f"{org_uri}",
                "scope": "organization",
            },
        )
        if "collection" in data:
            return data["collection"]
        else:
            return data

    def get_event(self, uuid):
        data = self.request("GET", f"/scheduled_events/{uuid}")
        return data

    def get_organization(self):
        data = self.request("GET", "/users/me")
        return data

    def execute_action(self, calendly_webhook_id: int):
        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.mentorship.models import CalendlyWebhook, CalendlyOrganization

        # example = {
        #     "created_at": "2020-11-23T17:51:19.000000Z",
        #     "created_by": "https://api.calendly.com/users/AAAAAAAAAAAAAAAA",
        #     "event": "invitee.created",
        #     "payload": {
        #     }
        # }

        webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()

        if not webhook:
            raise Exception("Invalid webhook id or not found")

        if not webhook.event or webhook.event == "":
            raise Exception("Impossible to determine event action, the webhook should have an event action string")

        webhook.organization = CalendlyOrganization.objects.filter(hash=webhook.organization_hash).first()
        if webhook.organization is None:
            raise Exception(f"Calendly organization with internal hash not found: {webhook.organization_hash}")

        action = webhook.event.replace(".", "_")

        logger.debug(f"Executing => {action}")
        if hasattr(actions, action):

            logger.debug("Action found")
            fn = getattr(actions, action)

            try:
                fn(self, webhook, webhook.payload)
                logger.debug("Mark action as done")
                webhook.status = "DONE"
                webhook.status_text = "OK"
                webhook.save()

            except Exception as e:
                logger.error("Mark action with error")

                webhook.status = "ERROR"
                webhook.status_text = "".join(traceback.format_exception(None, e, e.__traceback__))
                webhook.save()

        else:
            message = f"Action `{action}` is not implemented"
            logger.debug(message)

            webhook.status = "ERROR"
            webhook.status_text = message
            webhook.save()

            raise Exception(message)

    @staticmethod
    def add_webhook_to_log(context: dict, organization_hash: str):
        """Add one incoming webhook request to log"""

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.mentorship.models import CalendlyWebhook, CalendlyOrganization

        if not context or not len(context):
            return None

        webhook = CalendlyWebhook()

        if "event" not in context or context["event"] == "":
            raise Exception("Impossible to determine event action, the webhook should have an event action string")

        webhook.event = context["event"]
        webhook.created_by = context["created_by"]
        webhook.payload = context["payload"]
        webhook.called_at = context["created_at"]
        webhook.organization_hash = organization_hash
        webhook.status = "PENDING"

        organization = CalendlyOrganization.objects.filter(uri=context["created_by"]).first()
        if organization is not None:
            webhook.organization = organization

        webhook.save()

        return webhook
