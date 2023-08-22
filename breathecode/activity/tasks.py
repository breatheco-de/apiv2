from datetime import timedelta
import logging, os
from typing import Optional
from celery import shared_task, Task
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.utils.cohort_log import CohortDayLog
from breathecode.services.google_cloud.big_query import BigQuery
from breathecode.utils.decorators import task, AbortTask
from .models import StudentActivity
from breathecode.utils import NDB
from django.utils import timezone
from django.apps import apps

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


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
                 resource: Optional[str] = None,
                 resource_id: Optional[str | int] = None):
    from .models import Activity

    if (resource and not resource_id) or (resource_id and not resource):
        raise AbortTask('resource and resource_id must be both present or both absent')

    meta = {}
    timestamp = timezone.now()

    if resource:
        app_label, model_name = resource.split('.')
        model = apps.get_model(app_label, model_name)

    if resource and not model:
        raise AbortTask(f'{resource} is not a valid model')

    # fill meta based on resource and kind
    if resource == 'auth.User':
        user = model.objects.filter(id=resource_id).first()
        if not user:
            raise AbortTask(f'User {resource_id} not found')

        meta = {
            'email': user.email,
            'username': user.username,
        }

    duration = None

    if kind == 'login':
        duration = timedelta(days=1)

    with BigQuery.session() as session:
        session.add(
            Activity(user_id=user_id,
                     kind=kind,
                     resource=resource,
                     resource_id=resource_id,
                     meta=meta,
                     timestamp=timestamp,
                     duration=duration))
        session.commit()
