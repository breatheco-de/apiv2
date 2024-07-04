import functools
import logging
import os
import pickle
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

import zstandard
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
from google.cloud import bigquery
from redis.exceptions import LockError
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.activity import actions
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.utils.cohort_log import CohortDayLog
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils import NDB
from breathecode.utils.decorators import TaskPriority
from breathecode.utils.redis import Lock

from .models import StudentActivity


@functools.lru_cache(maxsize=1)
def get_activity_sampling_rate():
    env = os.getenv("ACTIVITY_SAMPLING_RATE")
    if env:
        return int(env)

    return 60


IS_DJANGO_REDIS = hasattr(cache, "delete_pattern")

API_URL = os.getenv("API_URL", "")

logger = logging.getLogger(__name__)

ISO_STRING_PATTERN = re.compile(
    r"^\d{4}-(0[1-9]|1[0-2])-([12]\d|0[1-9]|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\.\d{6}(Z|\+\d{2}:\d{2})?$"
)


@shared_task(bind=True, priority=TaskPriority.ACADEMY.value)
def get_attendancy_log(self, cohort_id: int):
    logger.info("Executing get_attendancy_log")
    cohort = Cohort.objects.filter(id=cohort_id).first()

    if not cohort:
        logger.error("Cohort not found")
        return

    if not cohort.syllabus_version:
        logger.error(f"Cohort {cohort.slug} does not have syllabus assigned")
        return

    try:
        # json has days?
        syllabus = cohort.syllabus_version.json["days"]

        # days is list?
        assert isinstance(syllabus, list)

        # the child has the correct attributes?
        for day in syllabus:
            assert isinstance(day["id"], int)
            duration_in_days = day.get("duration_in_days")
            assert isinstance(duration_in_days, int) or duration_in_days == None
            assert isinstance(day["label"], str)

    except Exception:
        logger.error(f"Cohort {cohort.slug} have syllabus with bad format")
        return

    client = NDB(StudentActivity)
    attendance = client.fetch([StudentActivity.cohort == cohort.slug, StudentActivity.slug == "classroom_attendance"])
    unattendance = client.fetch(
        [StudentActivity.cohort == cohort.slug, StudentActivity.slug == "classroom_unattendance"]
    )

    days = {}

    offset = 0
    current_day = 0
    for day in syllabus:
        if current_day > cohort.current_day:
            break

        for n in range(day.get("duration_in_days", 1)):
            current_day += 1
            if current_day > cohort.current_day:
                break

            attendance_ids = list([x["user_id"] for x in attendance if int(x["day"]) == current_day])
            unattendance_ids = list([x["user_id"] for x in unattendance if int(x["day"]) == current_day])
            has_attendance = bool(attendance_ids or unattendance_ids)

            days[day["label"]] = CohortDayLog(
                **{
                    "current_module": "unknown",
                    "teacher_comments": None,
                    "attendance_ids": attendance_ids if has_attendance else None,
                    "unattendance_ids": unattendance_ids if has_attendance else None,
                },
                allow_empty=True,
            ).serialize()

            if n:
                offset += 1

    cohort.history_log = days
    cohort.save_history_log()

    logger.info("History log saved")

    for cohort_user in CohortUser.objects.filter(cohort=cohort).exclude(educational_status="DROPPED"):
        get_attendancy_log_per_cohort_user.delay(cohort_user.id)


@shared_task(bind=False, priority=TaskPriority.ACADEMY.value)
def get_attendancy_log_per_cohort_user(cohort_user_id: int):
    logger.info("Executing get_attendancy_log_per_cohort_user")
    cohort_user = CohortUser.objects.filter(id=cohort_user_id).first()

    if not cohort_user:
        logger.error("Cohort user not found")
        return

    cohort = cohort_user.cohort
    user = cohort_user.user

    if not cohort.history_log:
        logger.error(f"Cohort {cohort.slug} has no log yet")
        return

    cohort_history_log = cohort.history_log or {}
    user_history_log = cohort_user.history_log or {}

    user_history_log["attendance"] = {}
    user_history_log["unattendance"] = {}

    for day in cohort_history_log:
        updated_at = cohort_history_log[day]["updated_at"]
        current_module = cohort_history_log[day]["current_module"]

        log = {
            "updated_at": updated_at,
            "current_module": current_module,
        }

        if user.id in cohort_history_log[day]["attendance_ids"]:
            user_history_log["attendance"][day] = log

        else:
            user_history_log["unattendance"][day] = log

    cohort_user.history_log = user_history_log
    cohort_user.save()

    logger.info("History log saved")


@task(bind=True, priority=TaskPriority.ACADEMY.value)
def upload_activities(self, task_manager_id: int, **_):

    def extract_data():
        nonlocal worker, res

        client = None
        if IS_DJANGO_REDIS:
            client = get_redis_connection("default")

        while True:
            try:
                with Lock(client, f"lock:activity:worker-{worker}", timeout=30, blocking_timeout=30):
                    worker_key = f"activity:worker-{worker}"
                    data = cache.get(worker_key)
                    cache.delete(worker_key)

                    if data:
                        data = zstandard.decompress(data)
                        data = pickle.loads(data)

                        res += data

            except LockError:
                raise RetryTask("Could not acquire lock for activity, operation timed out.")

            # this will keeping working even if the worker amount changes
            if worker >= workers and data is None:
                break

            worker += 1

    utc_now = timezone.now()
    limit = utc_now - timedelta(seconds=get_activity_sampling_rate())

    # prevent to run the same task multiple times before the sampling rate time
    task_cls = self.task_manager.__class__
    task_cls.objects.filter(
        status="SCHEDULED",
        task_module=self.task_manager.task_module,
        task_name=self.task_manager.task_name,
        created_at__lt=limit,
    ).exclude(id=task_manager_id).delete()

    workers = actions.get_workers_amount()
    res = []
    worker = 0

    has_not_backup = self.task_manager.status == "PENDING" and self.task_manager.attempts == 1
    backup_key = f"activity:backup:{task_manager_id}"

    if has_not_backup:
        extract_data()

    else:
        backup_key = f"activity:backup:{task_manager_id}"
        data = cache.get(backup_key)

        if data:
            data = zstandard.decompress(data)
            data = pickle.loads(data)

            res = data

        else:
            has_not_backup = True
            extract_data()

    if not res:
        # has backup
        if not has_not_backup:
            cache.delete(backup_key)

        raise AbortTask("No data to upload")

    table = BigQuery.table("activity")
    schema = table.schema()

    rows = [x["data"] for x in res]
    new_schema = BigQuery.join_schemas(*[x["schema"] for x in res])

    diff = BigQuery.schema_difference(schema, new_schema)

    try:
        if diff:
            merged_schema = BigQuery.merge_schema(diff, schema)
            table.update_schema(merged_schema)

        table.bulk_insert(rows)

    except Exception as e:
        data = pickle.dumps(res)
        data = zstandard.compress(data)

        cache.set(backup_key, data)
        raise e


@task(priority=TaskPriority.BACKGROUND.value)
def add_activity(
    user_id: int,
    kind: str,
    related_type: Optional[str] = None,
    related_id: Optional[str | int] = None,
    related_slug: Optional[str] = None,
    timestamp: Optional[str] = None,
    **_,
):

    logger.info(f"Executing add_activity related to {str(kind)}")

    if timestamp is None:
        timestamp = timezone.now().isoformat()

    if related_type and not (bool(related_id) ^ bool(related_slug)):
        raise AbortTask(
            "If related_type is provided, either related_id or related_slug must be provided, but not both."
        )

    if not related_type and (related_id or related_slug):
        raise AbortTask("If related_type is not provided, both related_id and related_slug must also be absent.")

    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection("default")

    worker = actions.get_current_worker_number()

    try:
        with Lock(client, f"lock:activity:worker-{worker}", timeout=30, blocking_timeout=30):
            worker_storage_key = f"activity:worker-{worker}"
            data = cache.get(worker_storage_key)

            if data:
                data = zstandard.decompress(data)
                data = pickle.loads(data)

            else:
                data = []

            res = {
                "schema": [
                    bigquery.SchemaField("user_id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                    bigquery.SchemaField("kind", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                    bigquery.SchemaField("timestamp", bigquery.enums.SqlTypeNames.TIMESTAMP, "NULLABLE"),
                    bigquery.SchemaField(
                        "related",
                        bigquery.enums.SqlTypeNames.STRUCT,
                        "NULLABLE",
                        fields=[
                            bigquery.SchemaField("type", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                            bigquery.SchemaField("id", bigquery.enums.SqlTypeNames.INT64, "NULLABLE"),
                            bigquery.SchemaField("slug", bigquery.enums.SqlTypeNames.STRING, "NULLABLE"),
                        ],
                    ),
                ],
                "data": {
                    "id": uuid.uuid4().hex,
                    "user_id": user_id,
                    "kind": kind,
                    "timestamp": timestamp,
                    "related": {
                        "type": related_type,
                        "id": related_id,
                        "slug": related_slug,
                    },
                    "meta": {},
                },
            }

            fields = []

            meta = actions.get_activity_meta(kind, related_type, related_id, related_slug)

            for key in meta:
                t = bigquery.enums.SqlTypeNames.STRING

                # keep it adobe than the date conditional
                if isinstance(meta[key], datetime) or (
                    isinstance(meta[key], str) and ISO_STRING_PATTERN.match(meta[key])
                ):
                    t = bigquery.enums.SqlTypeNames.TIMESTAMP
                elif isinstance(meta[key], date):
                    t = bigquery.enums.SqlTypeNames.DATE
                elif isinstance(meta[key], str):
                    pass
                elif isinstance(meta[key], bool):
                    t = bigquery.enums.SqlTypeNames.BOOL
                elif isinstance(meta[key], int):
                    t = bigquery.enums.SqlTypeNames.INT64
                elif isinstance(meta[key], float):
                    t = bigquery.enums.SqlTypeNames.FLOAT64

                # res['data'].append(serialize_field(key, meta[key], t))
                # res.append(serialize_field(key, meta[key], t, struct='meta'))

                fields.append(bigquery.SchemaField(key, t))
                res["data"]["meta"][key] = meta[key]

            meta_field = bigquery.SchemaField("meta", bigquery.enums.SqlTypeNames.STRUCT, "NULLABLE", fields=fields)
            # meta_field = bigquery.SchemaField('meta', 'STRUCT', 'NULLABLE', fields=fields)
            res["schema"].append(meta_field)
            # res['schema']['meta'] = meta_field

            data.append(res)
            data = pickle.dumps(data)
            data = zstandard.compress(data)

            cache.set(worker_storage_key, data)

    except LockError:
        raise RetryTask("Could not acquire lock for activity, operation timed out.")
