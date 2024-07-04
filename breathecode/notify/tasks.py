import json
import logging
import os
from datetime import datetime
from decimal import Decimal

import requests
from celery import shared_task
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from task_manager.core.exceptions import AbortTask
from task_manager.django.decorators import task

from breathecode.authenticate.models import Token
from breathecode.mentorship.models import MentorshipSession
from breathecode.notify import actions
from breathecode.services.slack.client import Slack
from breathecode.utils.decorators import TaskPriority

from .actions import sync_slack_team_channel, sync_slack_team_users


def get_api_url():
    return os.getenv("API_URL", "")


logger = logging.getLogger(__name__)


@shared_task(priority=TaskPriority.REALTIME.value)
def async_slack_team_channel(team_id):
    logger.debug("Starting async_slack_team_channel")
    return sync_slack_team_channel(team_id)


@shared_task(priority=TaskPriority.REALTIME.value)
def send_mentorship_starting_notification(session_id):
    logger.debug("Starting send_mentorship_starting_notification")

    session = MentorshipSession.objects.filter(id=session_id, mentee__isnull=False).first()
    if not session:
        logger.error(f"No mentorship session found for {session_id}")
        return False

    token, created = Token.get_or_create(session.mentor.user, token_type="temporal", hours_length=2)

    actions.send_email_message(
        "message",
        session.mentor.user.email,
        {
            "SUBJECT": "Mentorship session starting",
            "MESSAGE": f"Mentee {session.mentee.first_name} {session.mentee.last_name} is joining your session, please come back to this email when the session is over to marke it as completed",
            "BUTTON": "Finish and review this session",
            "LINK": f"{get_api_url()}/mentor/session/{session.id}?token={token.key}",
        },
        academy=session.mentor.academy,
    )

    return True


@shared_task(priority=TaskPriority.REALTIME.value)
def async_slack_team_users(team_id):
    logger.debug("Starting async_slack_team_users")
    return sync_slack_team_users(team_id)


@shared_task(priority=TaskPriority.REALTIME.value)
def async_slack_action(post_data):
    logger.debug("Starting async_slack_action")
    try:
        client = Slack()
        success = client.execute_action(context=post_data)
        if success:
            logger.debug("Successfully process slack action")
            return True
        else:
            logger.error("Error processing slack action")
            return False

    except Exception:
        logger.exception("Error processing slack action")
        return False


@shared_task(priority=TaskPriority.REALTIME.value)
def async_slack_command(post_data):
    logger.debug("Starting async_slack_command")
    try:
        client = Slack()
        success = client.execute_command(context=post_data)
        if success:
            logger.debug("Successfully process slack command")
            return True
        else:
            logger.error("Error processing slack command")
            return False

    except Exception:
        logger.exception("Error processing slack command")
        return False


@task(priority=TaskPriority.DEFAULT.value)
def async_deliver_hook(target, payload, hook_id=None, **kwargs):
    """
    Deliver a hook.

    target:     the url to receive the payload.
    payload:    a python primitive data structure
    instance:   a possibly null "trigger" instance
    hook:       the defining Hook object (useful for removing)
    """

    from .utils.hook_manager import HookManager

    def parse_payload(payload: dict):
        if not isinstance(payload, dict):
            return payload

        for key in payload.keys():
            # TypeError("string indices must be integers, not 'str'")
            if isinstance(payload[key], datetime):
                payload[key] = payload[key].isoformat().replace("+00:00", "Z")

            elif isinstance(payload[key], Decimal):
                payload[key] = str(payload[key])

            elif isinstance(payload[key], list) or isinstance(payload[key], tuple) or isinstance(payload[key], set):
                l = []
                for item in payload[key]:
                    l.append(parse_payload(item))

                payload[key] = l

            elif isinstance(payload[key], dict):
                payload[key] = parse_payload(payload[key])

        return payload

    logger.info("Starting async_deliver_hook")

    try:
        if isinstance(payload, dict):
            payload = parse_payload(payload)

        elif isinstance(payload, list):
            l = []
            for item in payload:
                l.append(parse_payload(item))

            payload = l

        encoded_payload = json.dumps(payload, cls=DjangoJSONEncoder)
        response = requests.post(
            url=target, data=encoded_payload, headers={"Content-Type": "application/json"}, timeout=2
        )

        if hook_id:
            hook_model_cls = HookManager.get_hook_model()
            hook = hook_model_cls.objects.get(id=hook_id)
            if response.status_code == 410:
                hook.delete()

            else:

                data = hook.sample_data
                if not isinstance(data, list):
                    data = []

                if "data" in payload and isinstance(payload["data"], dict):
                    data.append(payload["data"])
                elif isinstance(payload, dict):
                    data.append(json.loads(encoded_payload))

                if len(data) > 10:
                    data = data[1:10]

                hook.last_response_code = response.status_code
                hook.last_call_at = timezone.now()
                hook.sample_data = data
                hook.total_calls = hook.total_calls + 1
                hook.save()

    except Exception:
        logger.error(payload)
        raise AbortTask(f"Error while trying to save hook call with status code {response.status_code}. {payload}")
