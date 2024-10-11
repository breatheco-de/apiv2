import logging

import requests
from requests.exceptions import JSONDecodeError

logger = logging.getLogger(__name__)

AC_MAPS = {
    "email": "EMAIL",
    "first_name": "FIRSTNAME",
    "last_name": "LASTNAME",
    "phone": "PHONE",  # or "WHATSAPP", "SMS" depending on your needs
    "utm_location": "UTM_LOCATION",
    "utm_country": "COUNTRY",
    "utm_campaign": "UTM_CAMPAIGN",
    "utm_content": "UTM_CONTENT",
    "utm_medium": "UTM_MEDIUM",
    "utm_placement": "UTM_PLACEMENT",
    "utm_term": "UTM_TERM",
    "utm_source": "UTM_SOURCE",
    "utm_plan": "PLAN",
    "gender": "GENDER",
    "course": "COURSE",
    "gclid": "GCLID",
    "utm_url": "CONVERSION_URL",
    "utm_language": "LANGUAGE",
    "utm_landing": "LANDING_URL",
    "referral_key": "REFERRAL_KEY",
    "client_comments": None,  # It will be ignored because its none
    "current_download": None,  # It will be ignored because its none
}


def map_contact_keys(_contact):
    # Check if all keys in contact exist in AC_MAPS
    missing = []
    for key in _contact:
        if key not in AC_MAPS:
            missing.append(key)

    if len(missing) > 0:
        _keys = ",".join(missing)
        raise KeyError(f"The following keys are missing on AC_MAPS dictionary: '{_keys}'")

    # Replace keys in the contact dictionary based on AC_MAPS
    mapped_contact = {AC_MAPS[key]: value for key, value in _contact.items() if AC_MAPS[key] is not None}

    return mapped_contact


class BrevoAuthException(Exception):
    pass


class Brevo:
    HOST = "https://api.brevo.com/v3"
    headers = {}

    def __init__(self, token=None, org=None, host=None):
        self.token = token
        self.org = org
        self.page_size = 100
        if host is not None:
            self.HOST = host

    def get(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("GET", action_name, params=request_data)

    def head(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("HEAD", action_name, params=request_data)

    def post(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("POST", action_name, json=request_data)

    def delete(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("DELETE", action_name, params=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        self.headers = {
            "api-key": self.token,
            "Content-type": "application/json",
        }

        url = self.HOST + action_name
        resp = requests.request(method=method_name, url=url, headers=self.headers, params=params, json=json, timeout=2)

        if resp.status_code >= 200 and resp.status_code < 300:
            if method_name in ["DELETE", "HEAD"]:
                return resp

            try:
                data = resp.json()
                return data
            except JSONDecodeError:
                payload = resp.text
                return payload
        else:
            logger.debug(f"Error call {method_name}: /{action_name}")
            if resp.status_code == 401:
                raise BrevoAuthException("Invalid credentials when calling the Brevo API")

            error_message = str(resp.status_code)
            try:
                error = resp.json()
                error_message = error["message"]
                logger.debug(error)
            except Exception:
                pass

            raise Exception(
                f"Unable to communicate with Brevo API for {method_name} {action_name}, error: {error_message}"
            )

    # def create_contact(self, email: str, contact: dict, lists: list):

    #     try:
    #         body = {
    #             "attributes": {
    #                 **map_contact_keys(contact)
    #             },
    #             "updateEnabled": True,
    #             "email": email,
    #             "ext_id": attribution_id,
    #             "listIds": lists,
    #         }
    #         response = self.post("/contacts", request_data=body)
    #         return response.status_code == 201
    #     except Exception:
    #         return False

    def create_contact(self, contact: dict, automation_slug):
        try:
            body = {
                "event_name": "add_to_automation",
                "identifiers": {"email_id": contact["email"]},
                "contact_properties": {**map_contact_keys(contact)},
                "event_properties": {
                    "automation_slug": automation_slug,
                },
            }
            data = self.post("/events", request_data=body)
            return data
        except Exception as e:
            logger.exception("Error while creating contact in Brevo")
            raise e
            # return False
