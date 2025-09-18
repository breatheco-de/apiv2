---
trigger: glob
description:
globs: **/tasks.py
---

# Celery

- Django config file [settings.py](mdc:breathecode/settings.py)
- Celery config file [celery.py](mdc:breathecode/celery.py)
- [scheduler.mdc](mdc:.cursor/rules/scheduler.mdc) context
- Each task must handle only an instance of a model, do not iterate `Model.objects.filter(...)`, manage them using a Django Command, a Django Signal, a Django Admin Action, or using `schedule_task` https://breatheco-de.github.io/celery-task-manager-django-plugin/getting-started/schedule-tasks/
- Avoid async code within Celery Tasks
- Use the `task` decorator for declaring Celery Tasks, use the exceptions like `AbortTask` and `RetryTask` to manage the flow of the task https://breatheco-de.github.io/celery-task-manager-django-plugin/getting-started/task/
