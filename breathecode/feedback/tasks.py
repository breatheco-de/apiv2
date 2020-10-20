from celery import shared_task, Task
from breathecode.admissions.models import CohortUser
from .actions import send_survey
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task(bind=True, base=BaseTaskWithRetry)
def send_cohort_survey(self,cohort_id):
    cohort_users = CohortUser.objects.filter(cohort__id=cohort_id)
    logger.debug(f"Sending survey for {str(cohort_users.count())} students")
    for cu in cohort_users:
        try:
            result = send_survey(cu.user, cu.cohort)
            if result:
                logger.info(f"Survey successfully sent for {str(cu.user.id)} cohort {str(cu.cohort.id)}")
                return True
            else:
                logger.warning(f"Problem sending survey to {str(cu.user.id)} cohort {str(cu.cohort.id)}")
                return False
        except Exception:
            logger.exception(f"Error sending survey to {str(cu.user.id)} cohort {str(cu.cohort.id)}")
