from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.admissions.models import CohortUser
from breathecode.certificate.models import UserSpecialty
from breathecode.utils import getLogger
from breathecode.utils.decorators import TaskPriority

# Get an instance of a logger
logger = getLogger(__name__)


@task(bind=True, priority=TaskPriority.CERTIFICATE.value)
def take_screenshot(self, certificate_id, **_):
    logger.debug("Starting take_screenshot")
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot

    certificate_screenshot(certificate_id)


@task(bind=True, priority=TaskPriority.CERTIFICATE.value)
def remove_screenshot(self, certificate_id, **_):
    from .actions import remove_certificate_screenshot

    logger.info("Starting remove_screenshot")

    try:
        res = remove_certificate_screenshot(certificate_id)
    except UserSpecialty.DoesNotExist:
        raise RetryTask(f"UserSpecialty {certificate_id} does not exist")

    if res is False:
        raise AbortTask("UserSpecialty does not have any screenshot, it is skipped")


@task(bind=True, priority=TaskPriority.CERTIFICATE.value)
def reset_screenshot(self, certificate_id, **_):
    logger.debug("Starting reset_screenshot")
    # unittest.mock.patch is poor applying mocks
    from .actions import certificate_screenshot, remove_certificate_screenshot

    # just in case, wait for certificate to save
    remove_certificate_screenshot(certificate_id)
    certificate_screenshot(certificate_id)


@task(bind=True, priority=TaskPriority.CERTIFICATE.value)
def generate_cohort_certificates(self, cohort_id, **_):
    logger.debug("Starting generate_cohort_certificates")
    from .actions import generate_certificate

    cohort_users = CohortUser.objects.filter(cohort__id=cohort_id, role="STUDENT")

    logger.debug(f"Generating certificate for {str(cohort_users.count())} students that GRADUATED")
    for cu in cohort_users:
        try:
            generate_certificate(cu.user, cu.cohort)
        except Exception:
            logger.exception(f"Error generating certificate for {str(cu.user.id)} cohort {str(cu.cohort.id)}")


@task(bind=True, priority=TaskPriority.CERTIFICATE.value)
def async_generate_certificate(self, cohort_id, user_id, layout=None, **_):
    logger.info("Starting generate_cohort_certificates", slug="starting-generating-certificate")
    from .actions import generate_certificate

    cohort_user = CohortUser.objects.filter(cohort__id=cohort_id, user__id=user_id, role="STUDENT").first()

    if not cohort_user:
        logger.error(f"Cant generate certificate with {user_id}", slug="cohort-user-not-found")
        return

    logger.info(
        f"Generating gertificate for {str(cohort_user.user)} student that GRADUATED", slug="generating-certificate"
    )
    try:
        generate_certificate(cohort_user.user, cohort_user.cohort, layout)

    except Exception:
        logger.exception(
            f"Error generating certificate for {str(cohort_user.user.id)}, cohort {str(cohort_user.cohort.id)}",
            slug="error-generating-certificate",
        )
