# Tasks

A task is a code block that is executed in the [Celery](./introduction.md) process, you usually go to use the tasks within a [Django command](../django/commands.md), inside an [action](../4geeks/actions.md) or inside a [Django view](../django-rest-framework/views.md). It is used to implement [asynchronicity](<https://en.wikipedia.org/wiki/Asynchrony_(computer_programming)>) within the Django [process](<https://en.wikipedia.org/wiki/Process_(computing)>).

# Writing tasks

Read [this](https://docs.celeryq.dev/en/stable/userguide/tasks.html#basics)

## Where is the task?

It where in `breathecode/APP_NAME/tasks.py`.
