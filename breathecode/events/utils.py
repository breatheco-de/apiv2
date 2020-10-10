import os, requests


class Eventbrite(object):

    def __init__(self, token = None):
        if token is None:
            token = os.getenv('EVENTBRITE_KEY',None)

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

    def request(self, _type, url):

        headers = { **self.headers }
        response = requests.request(_type, self.host + url, headers=headers)
        result = response.json()
        if 'status_code' in result and result['status_code'] >= 400:
            raise Exception(result['error_description'])

        return result
        
    def get_my_organizations(self):
        data = self.request('GET', f"/users/me/organizations/")
        return data

    def get_organization_events(self, organization_id):
        data = self.request('GET', f"/organizations/{str(organization_id)}/events/")
        return data
        
    def get_organization_venues(self, organization_id):
        data = self.request('GET', f"/organizations/{str(organization_id)}/venues/")
        return data