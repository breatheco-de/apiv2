# Application

[Celery](../../essential/celery/introduction.md) needs an object called application, this object is bound with a set of configurations like the [Message Broker](https://en.wikipedia.org/wiki/Message_broker) or [task queue](<https://en.wikipedia.org/wiki/Scheduling_(computing)#task_queue>), theoretically you should have many celery apps and bound your tasks to one or many of those apps, actually we had not got any use to this feature and we rather use the [shared_task](https://docs.celeryq.dev/en/stable/userguide/tasks.html#how-do-i-import-the-task-decorator) decorator instead which just support one application.

## Setting up an application

Read [this](https://docs.celeryq.dev/en/stable/userguide/application.html).

## Where is the application?

It where in `breathecode/celery.py`.
