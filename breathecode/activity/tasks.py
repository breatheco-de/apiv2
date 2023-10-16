from datetime import date, datetime
import logging, os
import re
from typing import Optional
from uuid import uuid4
from celery import shared_task, Task
from breathecode.activity import actions
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.utils.cohort_log import CohortDayLog
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils.decorators import task, AbortTask
from .models import StudentActivity
from breathecode.utils import NDB
from django.utils import timezone
from google.cloud import bigquery

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)

ISO_STRING_PATTERN = re.compile(
    r'^\d{4}-(0[1-9]|1[0-2])-([12]\d|0[1-9]|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\.\d{6}(Z|\+\d{2}:\d{2})?$'
)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def get_attendancy_log(self, cohort_id: int):
    logger.info('Executing get_attendancy_log')
    cohort = Cohort.objects.filter(id=cohort_id).first()

    if not cohort:
        logger.error('Cohort not found')
        return

    if not cohort.syllabus_version:
        logger.error(f'Cohort {cohort.slug} does not have syllabus assigned')
        return

    try:
        # json has days?
        syllabus = cohort.syllabus_version.json['days']

        # days is list?
        assert isinstance(syllabus, list)

        # the child has the correct attributes?
        for day in syllabus:
            assert isinstance(day['id'], int)
            duration_in_days = day.get('duration_in_days')
            assert isinstance(duration_in_days, int) or duration_in_days == None
            assert isinstance(day['label'], str)

    except Exception:
        logger.error(f'Cohort {cohort.slug} have syllabus with bad format')
        return

    client = NDB(StudentActivity)
    attendance = client.fetch(
        [StudentActivity.cohort == cohort.slug, StudentActivity.slug == 'classroom_attendance'])
    unattendance = client.fetch(
        [StudentActivity.cohort == cohort.slug, StudentActivity.slug == 'classroom_unattendance'])

    days = {}

    offset = 0
    current_day = 0
    for day in syllabus:
        if current_day > cohort.current_day:
            break

        for n in range(day.get('duration_in_days', 1)):
            current_day += 1
            if current_day > cohort.current_day:
                break

            attendance_ids = list([x['user_id'] for x in attendance if int(x['day']) == current_day])
            unattendance_ids = list([x['user_id'] for x in unattendance if int(x['day']) == current_day])
            has_attendance = bool(attendance_ids or unattendance_ids)

            days[day['label']] = CohortDayLog(**{
                'current_module': 'unknown',
                'teacher_comments': None,
                'attendance_ids': attendance_ids if has_attendance else None,
                'unattendance_ids': unattendance_ids if has_attendance else None
            },
                                              allow_empty=True).serialize()

            if n:
                offset += 1

    cohort.history_log = days
    cohort.save_history_log()

    logger.info('History log saved')

    for cohort_user in CohortUser.objects.filter(cohort=cohort).exclude(educational_status='DROPPED'):
        get_attendancy_log_per_cohort_user.delay(cohort_user.id)


@shared_task(bind=False, base=BaseTaskWithRetry)
def get_attendancy_log_per_cohort_user(cohort_user_id: int):
    logger.info('Executing get_attendancy_log_per_cohort_user')
    cohort_user = CohortUser.objects.filter(id=cohort_user_id).first()

    if not cohort_user:
        logger.error('Cohort user not found')
        return

    cohort = cohort_user.cohort
    user = cohort_user.user

    if not cohort.history_log:
        logger.error(f'Cohort {cohort.slug} has no log yet')
        return

    cohort_history_log = cohort.history_log or {}
    user_history_log = cohort_user.history_log or {}

    user_history_log['attendance'] = {}
    user_history_log['unattendance'] = {}

    for day in cohort_history_log:
        updated_at = cohort_history_log[day]['updated_at']
        current_module = cohort_history_log[day]['current_module']

        log = {
            'updated_at': updated_at,
            'current_module': current_module,
        }

        if user.id in cohort_history_log[day]['attendance_ids']:
            user_history_log['attendance'][day] = log

        else:
            user_history_log['unattendance'][day] = log

    cohort_user.history_log = user_history_log
    cohort_user.save()

    logger.info('History log saved')


@task()
def add_activity(user_id: int,
                 kind: str,
                 related_type: Optional[str] = None,
                 related_id: Optional[str | int] = None,
                 related_slug: Optional[str] = None,
                 **_):
    logger.info(f'Executing add_activity related to {str(kind)}')

    if related_type and not (bool(related_id) ^ bool(related_slug)):
        raise AbortTask(
            'If related_type is provided, either related_id or related_slug must be provided, but not both.')

    if not related_type and (related_id or related_slug):
        raise AbortTask(
            'If related_type is not provided, both related_id and related_slug must also be absent.')

    client, project_id, dataset = BigQuery.client()

    job_config = bigquery.QueryJobConfig(
        destination=f'{project_id}.{dataset}.activity',
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        query_parameters=[
            bigquery.ScalarQueryParameter('x__id', 'STRING',
                                          uuid4().hex),
            bigquery.ScalarQueryParameter('x__user_id', 'INT64', user_id),
            bigquery.ScalarQueryParameter('x__kind', 'STRING', kind),
            bigquery.ScalarQueryParameter('x__timestamp', 'TIMESTAMP',
                                          timezone.now().isoformat()),
            bigquery.ScalarQueryParameter('x__related_type', 'STRING', related_type),
            bigquery.ScalarQueryParameter('x__related_id', 'INT64', related_id),
            bigquery.ScalarQueryParameter('x__related_slug', 'STRING', related_slug),
        ])

    meta = actions.get_activity_meta(kind, related_type, related_id, related_slug)

    meta_struct = ''

    for key in meta:
        t = 'STRING'

        # keep it adobe than the date confitional
        if isinstance(meta[key], datetime) or (isinstance(meta[key], str)
                                               and ISO_STRING_PATTERN.match(meta[key])):
            t = 'TIMESTAMP'
        elif isinstance(meta[key], date):
            t = 'DATE'
        elif isinstance(meta[key], str):
            pass
        elif isinstance(meta[key], bool):
            t = 'BOOL'
        elif isinstance(meta[key], int):
            t = 'INT64'
        elif isinstance(meta[key], float):
            t = 'FLOAT64'

        job_config.query_parameters += [bigquery.ScalarQueryParameter(key, t, meta[key])]
        meta_struct += f'@{key} as {key}, '

    if meta_struct:
        meta_struct = meta_struct[:-2]

    query = f"""
        SELECT
            @x__id as id,
            @x__user_id as user_id,
            @x__kind as kind,
            @x__timestamp as timestamp,
            STRUCT(
                @x__related_type as type,
                @x__related_id as id,
                @x__related_slug as slug) as related,
            STRUCT({meta_struct}) as meta
    """

    client.query(query, job_config=job_config)
