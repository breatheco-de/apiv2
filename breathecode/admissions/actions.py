import logging
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

def update_cohort_timeslot(certificate_timeslot, cohort_timeslot):
    is_change = (
        cohort_timeslot.starting_at != certificate_timeslot.starting_at or
        cohort_timeslot.ending_at != certificate_timeslot.ending_at or
        cohort_timeslot.recurrent != certificate_timeslot.recurrent or
        cohort_timeslot.recurrency_type != certificate_timeslot.recurrency_type
    )

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
            parent__id=certificate_timeslot.id,
            cohort__id=cohort_id).first()

        if cohort_timeslot:
            update_cohort_timeslot(certificate_timeslot, cohort_timeslot)

        else:
            create_cohort_timeslot(certificate_timeslot, cohort_id)
