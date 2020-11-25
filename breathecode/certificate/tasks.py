import logging, time
from celery import shared_task, Task
from breathecode.admissions.models import CohortUser

# Get an instance of a logger
logger = logging.getLogger(__name__)

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True

@shared_task(bind=True, base=BaseTaskWithRetry)
def take_screenshot(self, certificate_id):
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot

    certificate_screenshot(certificate_id)
    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def remove_screenshot(self, certificate_id):
    # unittest.mock.patch is poor applying mocks
    from .actions import remove_certificate_screenshot

    remove_certificate_screenshot(certificate_id)
    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def reset_screenshot(self, certificate_id):
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot, remove_certificate_screenshot

    # just in case, wait for cetificate to save
    remove_certificate_screenshot(certificate_id)
    certificate_screenshot(certificate_id)

    return True

@shared_task(bind=True, base=BaseTaskWithRetry)
def generate_cohort_certificates(self, cohort_id):
    from .actions import generate_certificate

    cohort_users = CohortUser.objects.filter(cohort__id=cohort_id, role='STUDENT',
        educational_status='GRADUATED')
    logger.debug(f"Generating gertificate for {str(cohort_users.count())} students that GRADUATED")
    for cu in cohort_users:
        try:
            result = generate_certificate(cu.user, cu.cohort)
        except Exception:
            logger.exception(f"Error generating certificate for {str(cu.user.id)} cohort {str(cu.cohort.id)}")
