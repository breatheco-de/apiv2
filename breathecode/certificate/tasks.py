from breathecode.utils import getLogger
from breathecode.admissions.models import CohortUser
from breathecode.utils.decorators.task import TaskPriority, task

# Get an instance of a logger
logger = getLogger(__name__)


@task(bind=True, priority=TaskPriority.CERTIFICATE)
def take_screenshot(self, certificate_id, **_):
    logger.debug('Starting take_screenshot')
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot

    try:
        certificate_screenshot(certificate_id)
        return True
    except Exception:
        return False


@task(bind=True, priority=TaskPriority.CERTIFICATE)
def remove_screenshot(self, certificate_id, **_):
    from .actions import remove_certificate_screenshot

    logger.debug('Starting remove_screenshot')

    try:
        remove_certificate_screenshot(certificate_id)
    except Exception:
        return False

    return True


@task(bind=True, priority=TaskPriority.CERTIFICATE)
def reset_screenshot(self, certificate_id, **_):
    logger.debug('Starting reset_screenshot')
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot, remove_certificate_screenshot

    try:
        # just in case, wait for cetificate to save
        remove_certificate_screenshot(certificate_id)
        certificate_screenshot(certificate_id)
    except Exception:
        return False

    return True


@task(bind=True, priority=TaskPriority.CERTIFICATE)
def generate_cohort_certificates(self, cohort_id, **_):
    logger.debug('Starting generate_cohort_certificates')
    from .actions import generate_certificate

    cohort_users = CohortUser.objects.filter(cohort__id=cohort_id, role='STUDENT')

    logger.debug(f'Generating certificate for {str(cohort_users.count())} students that GRADUATED')
    for cu in cohort_users:
        try:
            generate_certificate(cu.user, cu.cohort)
        except Exception:
            logger.exception(f'Error generating certificate for {str(cu.user.id)} cohort {str(cu.cohort.id)}')


@task(bind=True, priority=TaskPriority.CERTIFICATE)
def generate_one_certificate(self, cohort_id, user_id, layout, **_):
    logger.info('Starting generate_cohort_certificates', slug='starting-generating-certificate')
    from .actions import generate_certificate

    cohort_user = CohortUser.objects.filter(cohort__id=cohort_id, user__id=user_id, role='STUDENT').first()

    if not cohort_user:
        logger.error(f'Cant generate certificate with {user_id}', slug='cohort-user-not-found')
        return

    logger.info(f'Generating gertificate for {str(cohort_user.user)} student that GRADUATED',
                slug='generating-certificate')
    try:
        generate_certificate(cohort_user.user, cohort_user.cohort, layout)

    except Exception:
        logger.exception(
            f'Error generating certificate for {str(cohort_user.user.id)}, cohort {str(cohort_user.cohort.id)}',
            slug='error-generating-certificate')
