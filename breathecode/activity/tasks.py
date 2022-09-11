import logging, os
from celery import shared_task
from breathecode.admissions.models import Cohort, CohortUser
from .models import Activity
from breathecode.utils import NDB

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


@shared_task
def get_attendancy_log(cohort_id: int):
    logger.info('Executing get_attendancy_log')
    cohort = Cohort.objects.filter(id=cohort_id).first()

    if not cohort:
        logger.error('Cohort not found')
        return

    if not cohort.syllabus_version:
        logger.error(f'Cohort {cohort.slug} not have syllabus too')
        return

    try:
        # json has days?
        syllabus = cohort.syllabus_version.json['days']

        # days is list?
        assert isinstance(syllabus, list)

        # the child has the correct attributes?
        for day in syllabus:
            assert isinstance(day['id'], int)
            assert isinstance(day['duration_in_days'], int)
            assert isinstance(day['label'], str)
    except:
        logger.error(f'Cohort {cohort.slug} have syllabus with bad format')
        return

    client = NDB(Activity)
    attendance = client.fetch([Activity.cohort == cohort.slug, Activity.slug == 'classroom_attendance'])
    unattendance = client.fetch([Activity.cohort == cohort.slug, Activity.slug == 'classroom_unattendance'])

    result = []

    offset = 0
    for day in syllabus:
        for n in range(day['duration_in_days']):
            attendance_ids = list([x['user_id'] for x in attendance if x['day'] == day['id'] + n + offset])
            unattendance_ids = list(
                [x['user_id'] for x in unattendance if x['day'] == day['id'] + n + offset])
            has_attendance = bool(attendance_ids or unattendance_ids)

            result.append({
                'current_module': day['label'],
                'attendance_ids': attendance_ids if has_attendance else None,
                'unattendance_ids': unattendance_ids if has_attendance else None,
            })

            if n:
                offset += 1

    cohort.history_log = result
    cohort.save()

    logger.info('History log saved')
