import requests, logging, re, os
from . import commands
from breathecode.services.slack.commands import student, cohort
logger = logging.getLogger(__name__)

class Slack:
    HOST = "https://slack.com/api/"
    headers = {}

    def __init__(self, token=None, command=None):
        self.token = token

    def get(self, action_name, request_data={}):
        return self._call("GET", action_name, params=request_data)

    def post(self, action_name, request_data={}):
        return self._call("POST", action_name, json=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        if self.token is None:
            raise Exception("Missing slack token")

        if method_name != "GET":
            self.headers = {
                "Authorization": "Bearer "+self.token,
                "Content-type": "application/json",
            }
        else:
            params = {
                "token": self.token,
                **params,
            }

        resp = requests.request(method=method_name,url=self.HOST+action_name, headers=self.headers,
            params=params, json=json)

        if resp.status_code == 200:
            data = resp.json()
            if data["ok"] == False:
                raise Exception("Slack API Error "+data["error"])
            else:
                logger.debug(f"Successfull call {method_name}: /{action_name}")
                return data
        else:
            raise Exception(f"Unable to communicate with Slack API, error: {resp.status_code}")

    def execute_command(self, context):

        patterns = {
            "users": r"\<@([^|]+)\|([^>]+)>",
            "command": r"^(\w+)\s?"
        }
        content = context["text"]
        response = {}

        _commands = re.findall(patterns["command"], content)
        if len(_commands) != 1:
            raise Exception("Imposible to determine command")

        matches = re.findall(patterns["users"], content)
        response["users"] = [u[0] for u in matches]

        response["context"] = context
        
        if hasattr(commands, _commands[0]):
            return getattr(commands, _commands[0]).execute(**response)
        else:
            commands.cohorts.execute(**response)
            raise Exception("No implementation has been found for this command")
