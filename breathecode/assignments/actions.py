import requests, os, logging
from .models import Task, User
from breathecode.admissions.models import CohortUser

logger = logging.getLogger(__name__)

HOST = os.environ.get("OLD_BREATHECODE_API")


def sync_student_tasks(user, cohort=None):

    if cohort is None:
        cu = CohortUser.objects.filter(user=user).exclude(
            cohort__slug__contains="prework").first()
        if cu is not None:
            cohort = cu.cohort

    response = requests.get(f"{HOST}/student/{user.email}/task/")
    if response.status_code != 200:
        raise Exception(f"Student {user.email} not found on the old API")

    tasks = response.json()
    task_type = {
        'assignment': 'PROJECT',
        'quiz': 'QUIZ',
        'lesson': 'LESSON',
        'replit': 'EXERCISE',
    }

    revision_status = {
        'None': 'PENDING',
        'pending': 'PENDING',
        'approved': 'APPROVED',
        'rejected': 'REJECTED',
    }

    task_status = {
        'pending': 'PENDING',
        'done': 'DONE',
    }

    syncronized = []
    for _task in tasks['data']:

        if _task['type'] not in task_type:
            raise Exception(f"Invalid task_type {_task['type']}")
        if _task['status'] not in task_status:
            raise Exception(f"Invalid status {_task['status']}")
        if str(_task['revision_status']) not in revision_status:
            raise Exception(
                f"Invalid revision_status {_task['revision_status']}")

        task = Task.objects.filter(
            user_id=user.id, associated_slug=_task['associated_slug']).first()
        if task is None:
            task = Task(user=user, )
            task.task_status = task_status[_task['status']]
            task.live_url = _task['live_url']
            task.github_url = _task['github_url']
            task.associated_slug = _task['associated_slug']
            task.title = _task['title']
            task.task_type = task_type[_task['type']]
            task.revision_status = revision_status[str(
                _task['revision_status'])]
            task.description = _task['description']
            task.cohort = cohort
            task.save()
            task.save()
        syncronized.append(task)
    logger.debug(f"Added {len(syncronized)} tasks for student {user.email}")
    return syncronized


def sync_cohort_tasks(cohort):

    synchronized = []
    cohort_users = CohortUser.objects.filter(cohort__id=cohort.id,
                                             role="STUDENT",
                                             educational_status__in=["ACTIVE"])
    for cu in cohort_users:
        try:
            tasks = sync_student_tasks(cu.user, cohort=cohort)
            synchronized = synchronized + tasks
        except:
            continue

    return synchronized
