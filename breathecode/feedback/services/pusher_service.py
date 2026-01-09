import logging
import os

import pusher
from django.conf import settings

logger = logging.getLogger(__name__)

_pusher_client = None


def get_pusher_client():
    """Get or create Pusher client instance."""
    global _pusher_client

    if _pusher_client is None:
        app_id = getattr(settings, "PUSHER_APP_ID", os.environ.get("PUSHER_APP_ID", ""))
        key = getattr(settings, "PUSHER_KEY", os.environ.get("PUSHER_KEY", ""))
        secret = getattr(settings, "PUSHER_SECRET", os.environ.get("PUSHER_SECRET", ""))
        cluster = getattr(settings, "PUSHER_CLUSTER", os.environ.get("PUSHER_CLUSTER", "us2"))

        if not app_id or not key or not secret:
            logger.warning("Pusher credentials not configured. Survey events will not be sent.")
            return None

        _pusher_client = pusher.Pusher(
            app_id=app_id,
            key=key,
            secret=secret,
            cluster=cluster,
            ssl=True,
        )

    return _pusher_client


def send_survey_event(user_id: int, survey_response_id: int, questions: list, trigger_context: dict):
    """
    Send survey event to Pusher for a specific user.

    Args:
        user_id: ID of the user to send the event to
        survey_response_id: ID of the SurveyResponse
        questions: List of questions from the survey configuration
        trigger_context: Context information about what triggered the survey
    """
    client = get_pusher_client()
    if client is None:
        logger.warning(f"Cannot send survey event to user {user_id}: Pusher not configured")
        return False

    try:
        channel = f"public-user-{user_id}"
        event = "survey"
        payload = {
            "survey_response_id": survey_response_id,
            "questions": questions,
            "trigger_context": trigger_context,
        }

        client.trigger(channel, event, payload)
        logger.info(f"Survey event sent to user {user_id} via Pusher channel {channel}")
        return True

    except Exception as e:
        logger.error(f"Error sending survey event to user {user_id}: {str(e)}", exc_info=True)
        return False

