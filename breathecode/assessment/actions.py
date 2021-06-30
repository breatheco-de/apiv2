from breathecode.notify.actions import send_email_message
import logging
from breathecode.authenticate.actions import create_token
from .models import UserAssessment

logger = logging.getLogger(__name__)


def send_assestment(user_assessment):

    token = create_token(user_assessment.user, hours_length=48)
    data = {
        "SUBJECT":
        user_assessment.assessment.title,
        "LINK":
        f"https://assessment.breatheco.de/{user_assessment.id}?token={token.key}"
    }
    send_email_message("assessment", user_assessment.user.email, data)

    logger.info(f"Survey was sent for user: {str(user_assessment.user.id)}")

    user_assessment.status = "SENT"
    user_assessment.save()

    return True
