import breathecode.services.eventbrite.actions
import requests, logging, re, os, json, inspect
# from .decorator import commands, actions
from breathecode.services.slack.commands import student, cohort
from breathecode.services.slack.actions import monitoring
logger = logging.getLogger(__name__)

class Eventbrite:
    # HOST = "https://slack.com/api/"
    headers = {}

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

        payload = context["config"]

        if "action" not in payload or not payload["action"]:
            raise Exception("Imposible to determine action")

        action = payload["action"]

        del payload["action"]
        del payload["endpoint_url"]
        
        logger.debug(f"Executing => {action}")
        if hasattr(actions, action):
            logger.debug(f"Action found")
            fn = getattr(actions, action)
            fn(payload)
        else:
            raise Exception("Action `{action}` is not implemented")
