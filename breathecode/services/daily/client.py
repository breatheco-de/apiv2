import logging, os, urllib, time
from django.utils import timezone

logger = logging.getLogger(__name__)


class DailyClient:
    headers = {}

    def __init__(self, token=None):
        if token is None:
            token = os.getenv("DAILY_API_KEY", "")

        self.host = os.getenv("DAILY_API_URL", "")
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def request(self, _type, url, headers=None, query_string=None, data=None):
        # wonderful way to fix one poor mocking system
        import requests

        if headers is None:
            headers = {}

        _headers = {**self.headers, **headers}
        _query_string = ""
        if query_string is not None:
            _query_string = "?" + urllib.parse.urlencode(query_string)

        response = requests.request(_type, self.host + url + _query_string, headers=_headers, json=data, timeout=2)
        result = response.json()

        if result is None:
            raise Exception("Unknown error when requesting meeting room")

        if ("status_code" in result and result["status_code"] >= 400) or "error" in result:
            raise Exception(result["error"] + ": " + result["info"])

        # if 'pagination' in result:
        #     print('has more items?', result['pagination']['has_more_items'])
        #     if result['pagination']['has_more_items']:
        #         print('Continuation: ', result['pagination']['continuation'])
        #         new_result = self.request(_type,
        #                                   url,
        #                                   query_string={
        #                                       **query_string, 'continuation':
        #                                       result['pagination']['continuation']
        #                                   })
        #         for key in new_result:
        #             print(key, type(new_result[key]) == 'list')
        #             if type(new_result[key]) == 'list':
        #                 new_result[key] = result[key] + new_result[key]
        #         result.update(new_result)

        return result

    def create_all_rooms(self):
        data = self.request("GET", "/v1/rooms")
        return data

    def create_room(self, name="", exp_in_seconds=3600, exp_in_epoch=None):

        # now timestamp in epoch
        epoc_now = time.mktime(timezone.now().timetuple())

        if exp_in_epoch is None:
            epoc_now = time.mktime(timezone.now().timetuple())
            payload = {"properties": {"exp": f"{str(epoc_now + exp_in_seconds)}"}}
        else:
            payload = {"properties": {"exp": f"{str(exp_in_epoch)}"}}

        if name != "":
            payload["properties"]["name"] = name

        data = self.request("POST", "/v1/rooms", data=payload)
        return data

    def extend_room(self, name="", exp_in_seconds=3600, exp_in_epoch=None):

        if exp_in_epoch is None:
            epoc_now = time.mktime(timezone.now().timetuple())
            payload = {"properties": {"exp": f"{str(epoc_now + exp_in_seconds)}"}}
        else:
            payload = {"properties": {"exp": f"{str(exp_in_epoch)}"}}

        data = self.request("POST", "/v1/rooms/" + name, data=payload)
        return data

    def get_room(self, name=""):
        epoc_now = time.mktime(timezone.now().timetuple())
        data = self.request("GET", "/v1/rooms/" + name)

        if epoc_now > data["config"]["exp"]:
            data["expired"] = True
        else:
            data["expired"] = False

        return data
