import breathecode.services.eventbrite.actions as actions
import requests, logging, re, os, json, inspect, urllib
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
        self.headers = {
            "Authorization": f"Bearer {token}"
        }

    def has_error(self):
        # {
        #     "error": "VENUE_AND_ONLINE",
        #     "error_description": "You cannot both specify a venue and set online_event",
        #     "status_code": 400
        # }     
        pass   

    def request(self, _type, url, headers={}, query_string=None):

        _headers = { **self.headers, **headers }
        _query_string = ""
        if query_string is not None:
            _query_string = "?" + urllib.parse.urlencode(query_string)
        
        response = requests.request(_type, self.host + url + _query_string, headers=_headers)
        result = response.json()

        if 'status_code' in result and result['status_code'] >= 400:
            raise Exception(result['error_description'])

        if "pagination" in result:
            print("has more items?", result["pagination"]["has_more_items"])
            if result["pagination"]["has_more_items"]:
                    print("Continuation: ", result["pagination"]["continuation"])
                    new_result = self.request(_type, url, query_string={ **query_string, "continuation": result["pagination"]["continuation"] })
                    for key in new_result:
                        print(key,type(new_result[key]) == "list")
                        if type(new_result[key]) == "list":
                            new_result[key] = result[key] + new_result[key]
                    result.update(new_result)

        return result
        
    def get_my_organizations(self):
        data = self.request('GET', f"/users/me/organizations/")
        return data

    def get_organization_events(self, organization_id):
        query_string = { "expand": "organizer", "status": "live" }
        data = self.request('GET', f"/organizations/{str(organization_id)}/events/", query_string=query_string)
        return data
        
    def get_organization_venues(self, organization_id):
        data = self.request('GET', f"/organizations/{str(organization_id)}/venues/")
        return data

    def execute_action(self, context):
        # example = {
        #     'api_url': 'https://www.eventbriteapi.com/{api-endpoint-to-fetch-object-details}/',
        #     'config': {
        #         'user_id': '154764716258',
        #         'action': 'test',
        #         'webhook_id': '5630182',
        #         'endpoint_url': 'https://8000-ed64b782-cdd5-479d-af25-8889ba085657.ws-us03.gitpod.io/v1/events/eventbrite/webhook'
        #     }
        # }

        payload = context["config"] if "config" in context else None
        api_url = context["api_url"] if "api_url" in context else None

        if "action" not in payload or not payload["action"]:
            raise Exception("Imposible to determine action")

        action = payload["action"]

        del payload["action"]
        del payload["endpoint_url"]
        
        logger.debug(f"Executing => {action}")
        if hasattr(actions, action):
            response = requests.get(api_url, headers=self.headers)
            json = response.json()
            logger.debug("Eventbrite response")
            logger.debug(json)


            logger.debug(f"Action found")
            fn = getattr(actions, action)
            fn(payload, json)
        else:
            raise Exception(f"Action `{action}` is not implemented")
