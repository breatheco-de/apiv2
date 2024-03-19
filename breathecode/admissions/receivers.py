# from django.db.models.signals import post_save
import logging
from typing import Any, Type

from django.dispatch import receiver

import breathecode.authenticate.actions as authenticate_actions
from breathecode.assignments.models import Task
from breathecode.assignments.signals import assignment_status_updated

from ..activity import tasks as activity_tasks
from .actions import get_assets_on_syllabus
from .models import Cohort, CohortUser
from .signals import cohort_log_saved, cohort_user_created

# add your receives here
logger = logging.getLogger(__name__)


@receiver(cohort_log_saved, sender=Cohort)
def process_cohort_history_log(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info('Processing Cohort history log for cohort: ' + str(instance.id))

    activity_tasks.get_attendancy_log.delay(instance.id)


@receiver(cohort_user_created, sender=Cohort)
async def new_cohort_user(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info('Processing Cohort history log for cohort: ' + str(instance.id))

    await authenticate_actions.send_webhook('rigobot',
                                            'cohort_user.created',
                                            user=instance.user,
                                            data={
                                                'user': {
                                                    'id': instance.user.id,
                                                    'email': instance.user.email,
                                                    'first_name': instance.user.first_name,
                                                    'last_name': instance.user.last_name,
                                                },
                                            })


@receiver(assignment_status_updated, sender=Task, weak=False)
def mark_saas_student_as_graduated(sender: Type[Task], instance: Task, **kwargs: Any):
    logger.info('Processing available as saas student\'s tasks and marking as GRADUATED if it is')

    if instance.cohort is None:
        return

    cohort = Cohort.objects.filter(id=instance.cohort.id).first()

    if not cohort.available_as_saas:
        return

    syllabus_assets = get_assets_on_syllabus(cohort.syllabus_version.id, True)
    how_many_mandatory_tasks = Task.objects.filter(cohort=cohort.id,
                                                   user=instance.user.id,
                                                   task_status='DONE',
                                                   associated_slug__in=syllabus_assets).count()

    if len(syllabus_assets) == how_many_mandatory_tasks:
        cohort_user = CohortUser.objects.filter(user=instance.user.id, cohort=cohort.id).first()
        cohort_user.educational_status = 'GRADUATED'
        cohort_user.save()
