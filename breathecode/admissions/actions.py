import logging
from django.db.models.query_utils import Q
from breathecode.services.google_cloud import Storage

BUCKET_NAME = "admissions-breathecode"
logger = logging.getLogger(__name__)


def get_bucket_object(file_name):
    if not file_name:
        return False

    storage = Storage()
    file = storage.file(BUCKET_NAME, file_name)
    return file.blob


def create_cohort_timeslot(certificate_timeslot, cohort_id):
    from breathecode.admissions.models import CohortTimeSlot
    cohort_timeslot = CohortTimeSlot(
        parent=certificate_timeslot,
        cohort_id=cohort_id,
        starting_at=certificate_timeslot.starting_at,
        ending_at=certificate_timeslot.ending_at,
        recurrent=certificate_timeslot.recurrent,
        recurrency_type=certificate_timeslot.recurrency_type)

    cohort_timeslot.save(force_insert=True)
    return cohort_timeslot


def update_cohort_timeslot(certificate_timeslot, cohort_timeslot):
    is_change = (
        cohort_timeslot.starting_at != certificate_timeslot.starting_at
        or cohort_timeslot.ending_at != certificate_timeslot.ending_at
        or cohort_timeslot.recurrent != certificate_timeslot.recurrent
        or cohort_timeslot.recurrency_type !=
        certificate_timeslot.recurrency_type)

    if not is_change:
        return

    cohort_timeslot.starting_at = certificate_timeslot.starting_at
    cohort_timeslot.ending_at = certificate_timeslot.ending_at
    cohort_timeslot.recurrent = certificate_timeslot.recurrent
    cohort_timeslot.recurrency_type = certificate_timeslot.recurrency_type

    cohort_timeslot.save()


def create_or_update_cohort_timeslot(certificate_timeslot):
    from breathecode.admissions.models import Cohort, CohortTimeSlot

    cohort_ids = Cohort.objects.filter(
        syllabus__certificate__id=certificate_timeslot.certificate.id)\
            .values_list('id', flat=True)

    for cohort_id in cohort_ids:
        cohort_timeslot = CohortTimeSlot.objects.filter(
            parent__id=certificate_timeslot.id, cohort__id=cohort_id).first()

        if cohort_timeslot:
            update_cohort_timeslot(certificate_timeslot, cohort_timeslot)

        else:
            create_cohort_timeslot(certificate_timeslot, cohort_id)


def fill_cohort_timeslot(certificate_timeslot, cohort_id):
    from breathecode.admissions.models import CohortTimeSlot
    cohort_timeslot = CohortTimeSlot(
        cohort_id=cohort_id,
        starting_at=certificate_timeslot.starting_at,
        ending_at=certificate_timeslot.ending_at,
        recurrent=certificate_timeslot.recurrent,
        recurrency_type=certificate_timeslot.recurrency_type)

    return cohort_timeslot


def append_cohort_id_if_not_exist(cohort_timeslot):
    from breathecode.admissions.models import CohortTimeSlot

    if not cohort_timeslot.id:
        cohort_timeslot.id = CohortTimeSlot.objects.filter(
            created_at=cohort_timeslot.created_at,
            updated_at=cohort_timeslot.updated_at,
            cohort_id=cohort_timeslot.cohort_id,
            starting_at=cohort_timeslot.starting_at,
            ending_at=cohort_timeslot.ending_at,
            recurrent=cohort_timeslot.recurrent,
            recurrency_type=cohort_timeslot.recurrency_type).values_list(
                'id', flat=True).first()

    return cohort_timeslot


def sync_cohort_timeslots(cohort_id):
    from breathecode.admissions.models import CertificateTimeSlot, CohortTimeSlot, Cohort
    CohortTimeSlot.objects.filter(cohort__id=cohort_id).delete()

    cohort_values = Cohort.objects.filter(id=cohort_id).values(
        'academy__id', 'syllabus__certificate__id').first()

    certificate_timeslots = CertificateTimeSlot.objects.filter(
        academy__id=cohort_values['academy__id'],
        certificate__id=cohort_values['syllabus__certificate__id'])

    timeslots = CohortTimeSlot.objects.bulk_create([
        fill_cohort_timeslot(certificate_timeslot, cohort_id)
        for certificate_timeslot in certificate_timeslots
    ])

    return [append_cohort_id_if_not_exist(x) for x in timeslots]
