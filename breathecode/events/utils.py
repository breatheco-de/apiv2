import os
import urllib


class Eventbrite(object):

    def __init__(self, token=None):
        if token is None:
            token = os.getenv("EVENTBRITE_KEY", "")

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

    def request(self, _type, url, headers=None, query_string=None, data=None):
        import requests

        if headers is None:
            headers = {}

        _headers = {**self.headers, **headers}
        _query_string = "?" + urllib.parse.urlencode(query_string) if query_string else ""

        response = requests.request(_type, self.host + url + _query_string, headers=_headers, data=data, timeout=2)
        result = response.json()

        if "status_code" in result and result["status_code"] >= 400:
            raise Exception(result["error_description"])

        if "pagination" in result:
            print("has more items?", result["pagination"]["has_more_items"])
            if result["pagination"]["has_more_items"]:
                print("Continuation: ", result["pagination"]["continuation"])
                new_result = self.request(
                    _type, url, query_string={**query_string, "continuation": result["pagination"]["continuation"]}
                )
                for key in new_result:
                    print(key, type(new_result[key]) == "list")
                    if type(new_result[key]) == "list":
                        new_result[key] = result[key] + new_result[key]
                result.update(new_result)

        return result

    def get_my_organizations(self):
        data = self.request("GET", "/users/me/organizations/")
        return data

    def get_organization_events(self, organization_id):
        query_string = {"expand": "organizer,venue", "status": "live"}
        data = self.request("GET", f"/organizations/{str(organization_id)}/events/", query_string=query_string)
        return data

    def get_organization_venues(self, organization_id):
        data = self.request("GET", f"/organizations/{str(organization_id)}/venues/")
        return data

    # https://www.eventbrite.com/platform/api#/reference/event/create/create-an-event
    def create_organization_event(self, organization_id, data):
        data = self.request("POST", f"/organizations/{str(organization_id)}/events/", data=data)
        return data

    # https://www.eventbrite.com/platform/api#/reference/event/update/update-an-event
    def update_organization_event(self, event_id, data):
        data = self.request("PUT", f"/events/{event_id}/", data=data)
        return data

    # https://www.eventbrite.com/platform/api#/reference/event-description/retrieve/retrieve-full-html-description
    def get_event_description(self, event_id):
        data = self.request("GET", f"/events/{event_id}/structured_content/")
        return data

    # https://www.eventbrite.com/platform/api#/reference/event-description/retrieve/retrieve-full-html-description
    def create_or_update_event_description(self, event_id, version, data):
        data = self.request("POST", f"/events/{event_id}/structured_content/{version}/", data=data)
        return data
