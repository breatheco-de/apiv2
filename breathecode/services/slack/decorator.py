import re, sys, logging, inspect
from breathecode.services.slack import commands
from breathecode.services.slack import actions
from breathecode.authenticate.models import ProfileAcademy

logger = logging.getLogger(__name__)


def command(only=None):
    def decorator(function):
        def wrapper(*args, **kwargs):

            if "context" not in kwargs or kwargs["context"] is None:
                raise Exception("Missing scope information on slack command")
            context = kwargs["context"]

            profiles = None
            if only == "staff":
                profiles = ProfileAcademy.objects.filter(
                    user__slackuser__slack_id=context['user_id'],
                    academy__slackteam__slack_id=context['team_id']
                ).values_list('academy__id', flat=True)
                if len(profiles) == 0:
                    raise Exception(
                        f"Your user {context['user_id']} don't have permissions to query this student, are you a staff on this academy?"
                    )

            kwargs["academies"] = profiles
            kwargs["user_id"] = context['user_id']
            kwargs["team_id"] = context['team_id']
            kwargs["channel_id"] = context['channel_id']
            kwargs["text"] = context['text']

            result = function(*args, **kwargs)
            return result

        return wrapper

    return decorator


def action(only=None):
    def decorator(function):
        def wrapper(*args, **kwargs):
            if "payload" not in kwargs or kwargs["payload"] is None:
                raise Exception("Missing payload information on slack action")
            context = kwargs["payload"]

            profiles = None
            if only == "staff":
                profiles = ProfileAcademy.objects.filter(
                    user__slackuser__slack_id=context['user']['id'],
                    academy__slackteam__slack_id=context['team']
                    ['id']).values_list('academy__id', flat=True)
                if len(profiles) == 0:
                    raise Exception(
                        f"Your user {context['user']['id']} don't have permissions execute this action"
                    )

            kwargs["academies"] = profiles
            kwargs["user_id"] = context['user']['id']
            kwargs["type"] = context['type']
            kwargs["state"] = context['action_state']
            kwargs["team_id"] = context['team']['id']
            kwargs["channel_id"] = context['channel']['id']
            kwargs["actions"] = context['actions']
            kwargs.pop('payload', None)

            result = function(*args, **kwargs)
            return result

        return wrapper

    return decorator
