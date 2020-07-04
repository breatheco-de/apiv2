
import requests, os
from .models import Task, User

HOST = os.environ.get("OLD_BREATHECODE_API")
def sync_student_tasks(user):
    
    response = requests.get(f"{HOST}/student/{user.email}/task/")
    if response.status_code != 200:
        raise Exception(f"Student {user.email} not found new API")

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
    for _task in tasks['data']:
        if _task['type'] not in task_type:
            raise CommandError(f"Invalid task_type {_task['type']}")
        if _task['status'] not in task_status:
            raise CommandError(f"Invalid status {_task['status']}")
        if str(_task['revision_status']) not in revision_status:
            raise CommandError(f"Invalid revision_status {_task['revision_status']}")

        task = Task.objects.filter(user_id=user.id, associated_slug=_task['associated_slug']).first()
        if task is None:
            task = Task(
                user=user,
                associated_slug=_task['associated_slug'],
                title=_task['title'],
                task_status=task_status[_task['status']],
                task_type=task_type[_task['type']],
                revision_status=revision_status[str(_task['revision_status'])],
                github_url=_task['github_url'],
                live_url=_task['live_url'],
                description=_task['description'],
            )
            task.save()
        