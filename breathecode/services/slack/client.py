import requests, logging, re, os, json, inspect
from .decorator import commands, actions
from breathecode.services.slack.commands import student, cohort
from breathecode.services.slack.actions import monitoring
from .exceptions import SlackException

logger = logging.getLogger(__name__)


class Slack:
    HOST = 'https://slack.com/api/'
    headers = {}

    def __init__(self, token=None, command=None):
        self.token = token

    def get(self, action_name, request_data={}):
        return self._call('GET', action_name, params=request_data)

    def post(self, action_name, request_data={}):
        return self._call('POST', action_name, json=request_data)

    def _call(self, method_name, action_name, params=None, json=None):

        if self.token is None:
            raise Exception('Missing slack token')

        if method_name != 'GET':
            self.headers = {
                'Authorization': 'Bearer ' + self.token,
                'Content-type': 'application/json',
            }
        else:
            params = {
                'token': self.token,
                **params,
            }

        resp = requests.request(method=method_name,
                                url=self.HOST + action_name,
                                headers=self.headers,
                                params=params,
                                json=json)

        if resp.status_code == 200:
            data = resp.json()
            if data['ok'] == False:
                raise Exception('Slack API Error ' + data['error'])
            else:
                logger.debug(f'Successfull call {method_name}: /{action_name}')
                return data
        else:
            raise Exception(f'Unable to communicate with Slack API, error: {resp.status_code}')

    def execute_command(self, context):

        patterns = {'users': r'\<@([^|]+)\|([^>]+)>', 'command': r'^(\w+)\s?'}
        content = context['text']
        response = {}

        _commands = re.findall(patterns['command'], content)
        if len(_commands) != 1:
            raise SlackException('Imposible to determine command', slug='command-does-not-found')

        matches = re.findall(patterns['users'], content)
        response['users'] = [u[0] for u in matches]

        response['context'] = context

        if hasattr(commands, _commands[0]):
            return self._execute_command(commands, _commands[0], response)

        else:
            raise SlackException('No implementation has been found for this command',
                                 slug='command-does-not-exist')

    def _execute_command(self, module, command, response):

        return getattr(module, command).execute(**response)

    def execute_action(self, context):

        payload = json.loads(context['payload'])

        if 'actions' not in payload or len(payload['actions']) == 0:
            raise Exception('Impossible to determine action')

        try:
            logger.debug(f"Slack action: {str(payload['actions'])}")
            _data = json.loads(payload['actions'][0]['action_id'])
            action_class = _data.pop('class', None)
            method = _data.pop('method', None)
            payload['action_state'] = _data

        except:
            raise Exception(
                'Invalid slack action format, must be json with class and method properties at least')

        logger.debug(f'Executing {action_class} => {method}')
        if hasattr(actions, action_class):
            logger.debug(f'Action found')
            _module = getattr(actions, action_class)  #get action module

            if not hasattr(_module, action_class.capitalize()):
                raise Exception(f'Class {action_class.capitalize()} not found in module {action_class}')
            _class = getattr(_module, action_class.capitalize())(payload)  #factory the class

            if not hasattr(_class, method):
                raise Exception(
                    f'Method {method} not found in slack action class {action_class.capitalize()}')
            response = getattr(_class, method)(payload=payload)  # call action method

            if 'response_url' in payload and response:
                resp = requests.post(payload['response_url'], json=response)
                return resp.status_code == 200
            else:
                return True
        else:
            raise Exception(f'No implementation has been found for this action: {action_class}')
