import breathecode.services.eventbrite.actions as actions
import logging, re, os, json, inspect, urllib
# from .decorator import commands, actions
# from breathecode.services.eventbrite.commands import student, cohort
# from breathecode.services.eventbrite.actions import monitoring
logger = logging.getLogger(__name__)


class Eventbrite:
    # HOST = "https://slack.com/api/"
    headers = {}

    def __init__(self, token=None):
        if token is None:
            token = os.getenv('EVENTBRITE_KEY', "")

        self.host = "https://www.eventbriteapi.com/v3"
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def has_error(self):
        # {
        #     "error": "VENUE_AND_ONLINE",
        #     "error_description": "You cannot both specify a venue and set online_event",
        #     "status_code": 400
        # }
        pass

    def request(self, _type, url, headers={}, query_string=None):
        # wonderful way to fix one poor mocking system
        import requests

        _headers = {**self.headers, **headers}
        _query_string = ""
        if query_string is not None:
            _query_string = "?" + urllib.parse.urlencode(query_string)

        response = requests.request(_type,
                                    self.host + url + _query_string,
                                    headers=_headers)
        result = response.json()

        if 'status_code' in result and result['status_code'] >= 400:
            raise Exception(result['error_description'])

        if "pagination" in result:
            print("has more items?", result["pagination"]["has_more_items"])
            if result["pagination"]["has_more_items"]:
                print("Continuation: ", result["pagination"]["continuation"])
                new_result = self.request(
                    _type,
                    url,
                    query_string={
                        **query_string, "continuation":
                        result["pagination"]["continuation"]
                    })
                for key in new_result:
                    print(key, type(new_result[key]) == "list")
                    if type(new_result[key]) == "list":
                        new_result[key] = result[key] + new_result[key]
                result.update(new_result)

        return result

    def get_my_organizations(self):
        data = self.request('GET', f"/users/me/organizations/")
        return data

    def get_organization_events(self, organization_id):
        query_string = {"expand": "organizer", "status": "live"}
        data = self.request('GET',
                            f"/organizations/{str(organization_id)}/events/",
                            query_string=query_string)
        return data

    def get_organization_venues(self, organization_id):
        data = self.request('GET',
                            f"/organizations/{str(organization_id)}/venues/")
        return data

    def execute_action(self, eventbrite_webhook_id: int):
        # wonderful way to fix one poor mocking system
        import requests

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.events.models import EventbriteWebhook

        # example = {
        #     'api_url': 'https://www.eventbriteapi.com/{api-endpoint-to-fetch-object-details}/',
        #     'config': {
        #         'user_id': '154764716258',
        #         'action': 'test',
        #         'webhook_id': '5630182',
        #         'endpoint_url': 'https://8000-ed64b782-cdd5-479d-af25-8889ba085657.ws-us03.gitpod.io/v1/events/eventbrite/webhook'
        #     }
        # }

        webhook = EventbriteWebhook.objects.filter(
            id=eventbrite_webhook_id).first()

        if not webhook:
            raise Exception("Invalid webhook")

        if not webhook.action:
            raise Exception("Imposible to determine action")

        if not webhook.api_url:
            raise Exception("Imposible to determine api url")

        action = webhook.action.replace('.', '_')
        api_url = webhook.api_url
        # organization_id = webhook.organization_id

        logger.debug(f"Executing => {action}")
        if hasattr(actions, action):
            response = requests.get(api_url, headers=self.headers)
            json = response.json()

            # logger.debug("Eventbrite response")
            # logger.debug(json)

            logger.debug("Action found")
            fn = getattr(actions, action)

            try:
                fn(self, webhook, json)
                logger.debug("Mark action as done")
                webhook.status = 'DONE'
                webhook.save()

            except Exception as e:
                logger.debug("Mark action with error")

                # stack trace
                # import traceback
                # print(traceback.print_exc())
                # print(e)

                webhook.status = 'ERROR'
                webhook.status_text = str(e)
                webhook.save()

        else:
            message = f"Action `{action}` is not implemented"
            logger.debug(message)

            webhook.status = 'ERROR'
            webhook.status_text = message
            webhook.save()

            raise Exception(message)

    @staticmethod
    def add_webhook_to_log(context: dict, organization_id: str):
        """Add one incoming webhook request to log"""

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        from breathecode.events.models import EventbriteWebhook

        if not context or not len(context):
            return None

        webhook = EventbriteWebhook()
        context_has_config_key = 'config' in context
        context_has_api_url = 'api_url' in context

        if context_has_api_url:
            webhook.api_url = context['api_url']

        if context_has_config_key and 'user_id' in context['config']:
            webhook.user_id = context['config']['user_id']

        if context_has_config_key and 'action' in context['config']:
            webhook.action = context['config']['action']

        if context_has_config_key and 'webhook_id' in context['config']:
            webhook.webhook_id = context['config']['webhook_id']

        if context_has_config_key and 'endpoint_url' in context['config']:
            webhook.endpoint_url = context['config']['endpoint_url']

        webhook.organization_id = organization_id
        webhook.status = 'PENDING'
        webhook.save()

        return webhook
