from django.db.models.query_utils import Q
from breathecode.admissions.actions import create_or_update_cohort_timeslot
import logging
from celery import shared_task, Task
from .models import CertificateTimeSlot, Cohort
from breathecode.admissions.models import CohortTimeSlot

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def sync_cohort_timeslots(self, academy_id=None, academy_slug=None,
        certificate_id=None, certificate_slug=None):
    if (academy_id or academy_slug) and (certificate_id or certificate_slug):
        certificate_timeslots = CertificateTimeSlot.objects.filter(
            Q(academy__id=academy_id) | Q(academy__slug=academy_slug),
            Q(certificate__id=certificate_id) | Q(certificate__slug=certificate_slug))

    elif academy_id or academy_slug:
        certificate_timeslots = CertificateTimeSlot.objects.filter(
            Q(academy__id=academy_id) | Q(academy__slug=academy_slug))

    elif certificate_id or certificate_slug:
        certificate_timeslots = CertificateTimeSlot.objects.filter(
            Q(certificate__id=certificate_id) | Q(certificate__slug=certificate_slug))

    else:
        certificate_timeslots = []

    for certificate_timeslot in certificate_timeslots:
        create_or_update_cohort_timeslot(certificate_timeslot)
