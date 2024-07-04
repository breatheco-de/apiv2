import logging

from .exceptions import SlackException

logger = logging.getLogger(__name__)


def command(capable_of=None):
    from breathecode.authenticate.models import ProfileAcademy

    def decorator(function):

        def wrapper(*args, **kwargs):

            if "context" not in kwargs or kwargs["context"] is None:
                raise SlackException("Missing scope information on slack command", slug="context-missing")
            context = kwargs["context"]

            profiles = None
            if capable_of is not None:

                profiles = ProfileAcademy.objects.filter(
                    user__slackuser__slack_id=context["user_id"],
                    academy__slackteam__slack_id=context["team_id"],
                    role__capabilities__slug=capable_of,
                ).values_list("academy__id", flat=True)

                if len(profiles) == 0:
                    raise SlackException(
                        f"Your user {context['user_id']} don't have permissions to use this command, are you a staff or student on this academy?",
                        slug="unauthorized-user",
                    )

            kwargs["academies"] = profiles
            kwargs["user_id"] = context["user_id"]
            kwargs["team_id"] = context["team_id"]
            kwargs["channel_id"] = context["channel_id"]
            kwargs["text"] = context["text"]

            result = function(*args, **kwargs)
            return result

        return wrapper

    return decorator


def action(only=None):
    from breathecode.authenticate.models import ProfileAcademy

    def decorator(function):

        def wrapper(*args, **kwargs):
            if "payload" not in kwargs or kwargs["payload"] is None:
                raise Exception("Missing payload information on slack action")
            context = kwargs["payload"]

            profiles = None
            if only == "staff":
                profiles = ProfileAcademy.objects.filter(
                    user__slackuser__slack_id=context["user"]["id"], academy__slackteam__slack_id=context["team"]["id"]
                ).values_list("academy__id", flat=True)

                if len(profiles) == 0:
                    raise Exception(f"Your user {context['user']['id']} don't have permissions execute this action")

            kwargs["academies"] = profiles
            kwargs["user_id"] = context["user"]["id"]
            kwargs["type"] = context["type"]
            kwargs["state"] = context["action_state"]
            kwargs["team_id"] = context["team"]["id"]
            kwargs["channel_id"] = context["channel"]["id"]
            kwargs["actions"] = context["actions"]
            kwargs.pop("payload", None)

            result = function(*args, **kwargs)
            return result

        return wrapper

    return decorator
