import logging

from celery import shared_task

from breathecode.utils import TaskPriority

from .models import UserAssessment

# Get an instance of a logger
logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.ASSESSMENT.value)
def async_close_userassignment(self, ua_id):
    """Notify if the task was change."""
    logger.info("Starting async_close_userassignment")

    ua = UserAssessment.objects.filter(id=ua_id).first()
    if not ua:
        return False

    score, last_answer = ua.get_score()

    # Not one answer found for the user assessment
    if last_answer is None:
        ua.status = "ERROR"
        ua.status_text = "No answers found for this user assessment session"
        ua.save()
        return True

    ua.total_score = score
    ua.status = "ANSWERED"
    ua.status_text = ""
    ua.finished_at = last_answer.created_at
    ua.save()
    return True
