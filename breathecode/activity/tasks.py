from datetime import date, datetime
import functools
import msgpack
import logging, os
import re
from typing import Optional
import uuid
from celery import shared_task
import zstandard
from breathecode.activity import actions
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.utils.cohort_log import CohortDayLog
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils.decorators import task, AbortTask, TaskPriority, RetryTask
from .models import StudentActivity
from breathecode.utils import NDB
from django.utils import timezone
from google.cloud import bigquery
from django.core.cache import cache
from django_redis import get_redis_connection
from redis.exceptions import LockError
from breathecode.utils.redis import Lock


@functools.lru_cache(maxsize=1)
def get_activity_sampling_rate():
    env = os.getenv('ACTIVITY_SAMPLING_RATE')
    if env:
        return int(env)

    return 60


IS_DJANGO_REDIS = hasattr(cache, 'delete_pattern')

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)

ISO_STRING_PATTERN = re.compile(
    r'^\d{4}-(0[1-9]|1[0-2])-([12]\d|0[1-9]|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\.\d{6}(Z|\+\d{2}:\d{2})?$'
)


@shared_task(bind=True, priority=TaskPriority.ACADEMY.value)
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


@shared_task(bind=False, priority=TaskPriority.ACADEMY.value)
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


from google.cloud import bigquery
from google.cloud.bigquery.schema import SchemaField
from google.cloud.bigquery.table import Table


class BigQueryS:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return str(self.__dict__)

    @staticmethod
    def table() -> list[SchemaField]:
        # Your code here
        from google.cloud import bigquery

        # Initialize a BigQuery client
        client = bigquery.Client()

        # Define your project ID, dataset ID, and table ID
        project_id = 'your-project-id'
        dataset_id = 'your-dataset-id'
        table_id = 'your-table-id'

        # Construct a reference to the table
        table_ref = client.dataset(dataset_id, project=project_id).table(table_id)

        # Fetch the schema of the table
        table = client.get_table(table_ref)

        return table.schema

    @classmethod
    def schema(cls, table: Table | str) -> list[SchemaField]:
        if isinstance(table, str):
            table = cls.table()
            # client, project_id, dataset = BigQuery.client()
            # table = f'{project_id}.{dataset}.{table}'
            # table = client.get_table(table)
        return table.schema

    @classmethod
    def append_schema(cls, table: Table | str, new_fields):
        if isinstance(table, str):
            table = cls.table()

        client = bigquery.Client()

        # first implementation
        table.schema = table.schema + new_fields

        client.update_table(table, ['schema'])


@task(priority=TaskPriority.BACKGROUND.value)
def upload_activities(task_manager_id: int):
    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection('default')

    workers = actions.get_workers_amount()

    res = []

    processes_keys = 0

    while True:
        worker = 0

        try:
            with Lock(client, f'lock:activity:worker-{worker}', timeout=3, blocking_timeout=3):
                backup_key = f'activity:backup:{worker}-{task_manager_id}'
                worker_key = f'lock:activity:worker-{worker}'

                data = cache.get(backup_key)
                if not data:
                    data = cache.get(worker_key)
                    cache.set(backup_key, data)
                    cache.set(worker_key, None)

                data = zstandard.decompress(data)
                data = msgpack.loads(data)

        except LockError:
            raise RetryTask('Could not acquire lock for activity, operation timed out.')

        # this will keeping working even if the worker amount changes
        if worker >= workers and data is None:
            break

        processes_keys = worker
        worker += 1
        res += data

    if not data:
        cache.set(backup_key, None)
        raise AbortTask('No data to upload')

    client, project_id, dataset = BigQuery.client()

    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField('id', 'STRING'),
            bigquery.SchemaField('user_id', 'INT64'),
            bigquery.SchemaField('kind', 'STRING'),
            bigquery.SchemaField('timestamp', 'TIMESTAMP'),
            bigquery.SchemaField('related', 'STRUCT<type STRING, id INT64, slug STRING>'),
            bigquery.SchemaField(
                'meta', 'STRUCT<{}>'.format(', '.join([
                    'id STRING',
                    'user_id INT64',
                    'kind STRING',
                    'timestamp TIMESTAMP',
                    'related_type STRING',
                    'related_id INT64',
                    'related_slug STRING',
                ]))),
        ],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    table = f'{project_id}.{dataset}.activity'

    job = client.load_table_from_json(data, table, job_config=job_config)
    job.result()

    if job.error_result:
        raise Exception(job.error_result.get('message', 'No description'))

    for worker in range(processes_keys):
        cache.set(f'activity:backup:{worker}-{task_manager_id}', None)


@task(priority=TaskPriority.BACKGROUND.value)
def add_activity(user_id: int,
                 kind: str,
                 related_type: Optional[str] = None,
                 related_id: Optional[str | int] = None,
                 related_slug: Optional[str] = None,
                 **_):

    def serialize_field(field, value, type, prefix='', suffix='', struct=None):
        return {
            'key': prefix + field + suffix,
            'type': type,
            'value': value,
            'struct': struct,
        }

    logger.info(f'Executing add_activity related to {str(kind)}')

    if related_type and not (bool(related_id) ^ bool(related_slug)):
        raise AbortTask(
            'If related_type is provided, either related_id or related_slug must be provided, but not both.')

    if not related_type and (related_id or related_slug):
        raise AbortTask(
            'If related_type is not provided, both related_id and related_slug must also be absent.')

    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection('default')

    workers = actions.get_workers_amount()

    try:
        with Lock(client, 'lock:activity:current-worker', timeout=3, blocking_timeout=3):
            current_worker_key = 'activity:current-worker'
            worker = cache.get(current_worker_key)
            if worker is None or int(worker) == workers:
                worker = 0

            worker = int(worker)
            data = cache.set(current_worker_key, str(worker + 1))

    except LockError:
        worker = 0

    try:
        with Lock(client, f'lock:activity:worker-{worker}', timeout=3, blocking_timeout=3):
            worker_storage_key = f'activity:worker-{worker}'
            data = cache.get(worker_storage_key)

            if data:
                data = zstandard.decompress(data)
                data = msgpack.loads(data)

            else:
                data = []

            res = [
                serialize_field('id', uuid.uuid4().hex, 'STRING', struct='x', prefix='x__'),
                serialize_field('user_id', user_id, 'INT64', struct='x', prefix='x__'),
                serialize_field('kind', kind, 'STRING', struct='x', prefix='x__'),
                serialize_field('timestamp',
                                timezone.now().isoformat(),
                                'TIMESTAMP',
                                struct='x',
                                prefix='x__'),
                serialize_field('related_type', related_type, 'STRING', struct='x', prefix='x__'),
                serialize_field('related_id', related_id, 'INT64', struct='x', prefix='x__'),
                serialize_field('related_slug', related_slug, 'STRING', struct='x', prefix='x__'),
            ]

            meta = actions.get_activity_meta(kind, related_type, related_id, related_slug)

            for key in meta:
                t = 'STRING'

                # keep it adobe than the date conditional
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

                res.append(serialize_field(key, meta[key], t, struct='meta'))

            data.append(res)
            data = msgpack.dumps(data)
            data = zstandard.compress(data)

            cache.set(worker_storage_key, data)

    except LockError:
        raise RetryTask('Could not acquire lock for activity, operation timed out.')
