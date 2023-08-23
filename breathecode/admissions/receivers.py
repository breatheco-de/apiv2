# from django.db.models.signals import post_save
from typing import Any, Type
from django.dispatch import receiver

from breathecode.assignments.signals import assignment_status_updated
from breathecode.assignments.models import Task
from .models import Cohort, CohortUser
from .actions import get_assets_on_syllabus
from .signals import cohort_log_saved
from ..activity import tasks as activity_tasks
import logging

# add your receives here
logger = logging.getLogger(__name__)


@receiver(cohort_log_saved, sender=Cohort)
def process_cohort_history_log(sender: Type[Cohort], instance: Cohort, **kwargs: Any):
    logger.info('Processing Cohort history log for cohort: ' + str(instance.id))

    activity_tasks.get_attendancy_log.delay(instance.id)


@receiver(assignment_status_updated, sender=Task, weak=False)
def mark_saas_student_as_graduated(sender: Type[Task], instance: Task, **kwargs: Any):
    logger.info('Processing available as saas student\'s tasks and marking as GRADUATED if it is')

    if instance.cohort is None:
        return

    cohort = Cohort.objects.filter(id=instance.cohort.id).first()

    if not cohort.available_as_saas:
        return

    syllabus_assets = get_assets_on_syllabus(cohort.syllabus_version.id, True)
    tasks = Task.objects.filter(cohort=cohort.id, user=instance.user.id, task_status='DONE')

    if len(syllabus_assets) == len(tasks):
        cohort_user = CohortUser.objects.filter(user=instance.user.id, cohort=cohort.id).first()
        cohort_user.educational_status = 'GRADUATED'
        cohort_user.save()
