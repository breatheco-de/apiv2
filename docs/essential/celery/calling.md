# Calling

You can an existing task, [Celery](https://docs.celeryq.dev/en/stable/index.html) provides tree basic way to using its tasks:

Asynchronous way:

- Using `my_task.delay(...)`
- Using `my_task.apply_async(args=(...), kwargs={...})`

Synchronous way:

- Using `my_task(...)`

## Calling your task

Read [this](https://docs.celeryq.dev/en/stable/userguide/calling.html).

## Where is the task?

It where in `breathecode/APP_NAME/tasks.py`.
