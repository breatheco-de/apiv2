import requests, logging

logger = logging.getLogger(__name__)


class Facebook:
    HOST = "https://graph.facebook.com/v8.0/"
    headers = {}

    def __init__(self, token):
        self.token = token

    def get(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("GET", action_name, params=request_data)

    def post(self, action_name, request_data=None):

        if request_data is None:
            request_data = {}

        return self._call("POST", action_name, json=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        if method_name != "GET":
            self.headers = {
                "Authorization": "Bearer " + self.token,
                "Content-type": "application/json",
            }
        else:
            params = {
                "token": self.token,
                **params,
            }

        resp = requests.request(
            method=method_name, url=self.HOST + action_name, headers=self.headers, params=params, json=json, timeout=2
        )

        if resp.status_code == 200:
            data = resp.json()
            if data["ok"] == False:
                raise Exception("Slack API Error " + data["error"])
            else:
                logger.debug(f"Successfull call {method_name}: /{action_name}")
                return data
        else:
            raise Exception(f"Unable to communicate with Slack API, error: {resp.status_code}")
