import logging
from typing import Type

from django.conf import settings
from django.dispatch import receiver

from breathecode.authenticate.models import Token
from breathecode.notify.actions import send_email_message

from .models import MentorshipSession
from .signals import mentorship_session_status

logger = logging.getLogger(__name__)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentorship_session_completed(sender: Type[MentorshipSession], instance: MentorshipSession, **kwargs):
    """
    Send an email to the mentor when a mentorship session is marked as completed,
    asking them to fill out the session completion form.
    """
    if instance.status == "COMPLETED" and instance.mentor and instance.mentor.user:
        logger.debug(
            f"Mentorship session {instance.id} completed, sending email to mentor {instance.mentor.user.email}"
        )

        # Create a temporary token for the mentor to access the session completion form
        token, created = Token.get_or_create(instance.mentor.user, token_type="temporal", hours_length=24)

        # Get the API URL
        api_url = getattr(settings, "API_URL", "https://api.4geeks.com")

        # Build the session completion URL
        session_form_url = f"{api_url}/mentor/session/{instance.id}?token={token.key}"

        # Prepare mentee name
        mentee_name = "a student"
        if instance.mentee:
            mentee_name = f"{instance.mentee.first_name} {instance.mentee.last_name}".strip()
            if not mentee_name:
                mentee_name = instance.mentee.email or "a student"

        # Send the email
        send_email_message(
            "session_completed_mentor",
            instance.mentor.user.email,
            {
                "SUBJECT": "Please complete your mentorship session feedback",
                "MENTOR_NAME": f"{instance.mentor.user.first_name} {instance.mentor.user.last_name}".strip()
                or instance.mentor.user.email,
                "MENTEE_NAME": mentee_name,
                "SERVICE_NAME": instance.service.name if instance.service else "Mentorship Session",
                "SESSION_ID": instance.id,
                "BUTTON": "Complete Session Feedback",
                "LINK": session_form_url,
            },
            academy=instance.mentor.academy,
        )

        logger.info(f"Session completion email sent to mentor {instance.mentor.user.email} for session {instance.id}")
