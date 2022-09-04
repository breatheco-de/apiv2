import os
import logging
import re

from celery import shared_task, Task as CeleryTask

from breathecode.assignments.actions import task_is_valid_for_notifications, NOTIFICATION_STRINGS
import breathecode.notify.actions as actions
from .models import Task

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BaseTaskWithRetry(CeleryTask):
    autoretry_for = (Exception, )
    #                                              seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def student_task_notification(self, task_id):
    """Notify if the task was change"""
    logger.debug('Starting student_task_notification')

    task = Task.objects.filter(id=task_id).first()
    if not task_is_valid_for_notifications(task):
        return

    language = task.cohort.language
    revision_status = task.revision_status
    subject = NOTIFICATION_STRINGS[language]['student']['subject'].format(title=task.title)
    details = NOTIFICATION_STRINGS[language]['student'][revision_status]

    actions.send_email_message('diagnostic', task.user.email, {
        'subject': subject,
        'details': details,
    })


@shared_task(bind=True, base=BaseTaskWithRetry)
def teacher_task_notification(self, task_id):
    """Notify if the task was change"""
    logger.debug('Starting teacher_task_notification')

    url = os.getenv('TEACHER_URL')
    if not url:
        logger.error('TEACHER_URL is not set as environment variable')
        return

    url = re.sub('/$', '', url)

    task = Task.objects.filter(id=task_id).first()
    if not task_is_valid_for_notifications(task):
        return

    language = task.cohort.language
    subject = NOTIFICATION_STRINGS[language]['teacher']['subject'].format(first_name=task.user.first_name,
                                                                          last_name=task.user.last_name)

    details = NOTIFICATION_STRINGS[language]['teacher']['details'].format(
        first_name=task.user.first_name,
        last_name=task.user.last_name,
        title=task.title,
        url=f'{url}/cohort/{task.cohort.slug}/assignments')

    actions.send_email_message('diagnostic', task.user.email, {
        'subject': subject,
        'details': details,
    })
