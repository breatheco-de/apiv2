from __future__ import absolute_import, unicode_literals

# keeps this adobe
import newrelic.agent

newrelic.agent.initialize()

# the rest of your Celery file contents go here
import os
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from celery import Celery
from celery.signals import worker_process_init

from breathecode.setup import get_redis_config

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "breathecode.settings")

# django.setup()

settings, kwargs, REDIS_URL = get_redis_config()

app = Celery("celery_breathecode", **kwargs)
if os.getenv("ENV") == "test":
    app.conf.update(task_always_eager=True)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings")
app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    namespace="CELERY",
    result_expires=10,
    worker_max_memory_per_child=int(os.getenv("CELERY_MAX_MEMORY_PER_WORKER", "470000")),
    worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_WORKER", "1000")),
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.conf.broker_transport_options = {
    "priority_steps": list(range(11)),
    "sep": ":",
    "queue_order_strategy": "priority",
}


class Worker(TypedDict):
    pid: int
    created_at: datetime


Workers = dict[int, list[Worker]]
DataMap = dict[int, bool]


def get_workers_amount():
    dynos = int(os.getenv("CELERY_DYNOS") or 1)
    workers = int(os.getenv("CELERY_MAX_WORKERS") or 1)
    return dynos * workers


if os.getenv("ENV") != "test" and (WORKER := os.getenv("CELERY_POOL", "prefork")) not in ["prefork"]:
    raise ValueError(f'CELERY_POOL must be "prefork" but got {WORKER} that is not supported yet.')


def get_worker_id():
    if WORKER == "gevent":
        from gevent import getcurrent

        return id(getcurrent())
    return os.getpid()


@worker_process_init.connect
def worker_process_init_handler(**kwargs):
    from django.core.cache import cache
    from django_redis import get_redis_connection
    from redis.exceptions import LockError

    is_django_redis = hasattr(cache, "delete_pattern")
    if is_django_redis:
        from redis.lock import Lock

    else:

        class Lock:

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                pass

            def __exit__(self, *args, **kwargs):
                pass

    worker_id = get_worker_id()
    print(f"Worker process initialized with id: {worker_id}")

    client = None
    if is_django_redis:

        client = get_redis_connection("default")

    workers = get_workers_amount()
    delta = timedelta(minutes=2)

    # save the workers pid in cache for know its worker number
    while True:
        try:
            with Lock(client, "lock:workers", timeout=3, blocking_timeout=3):
                data: Workers = cache.get("workers")
                available: DataMap = {}
                if data is None:
                    data = {}

                for i in range(workers):
                    if i not in data:
                        data[i] = []

                    if len(data[i]) >= 2:
                        data[i].sort(key=lambda x: x["created_at"].replace(tzinfo=UTC))

                        if datetime.now(UTC) - data[i][-1]["created_at"].replace(tzinfo=UTC) < delta:
                            available[i] = False
                            data[i] = data[i][-2:]
                        else:
                            available[i] = True
                            data[i] = data[i][-1:]

                    elif len(data[i]) == 1:
                        if datetime.now(UTC) - data[i][0]["created_at"].replace(tzinfo=UTC) < delta:
                            available[i] = False
                        else:
                            available[i] = True

                    else:
                        available[i] = True

                found = False
                for i in range(workers):
                    if available[i]:
                        data[i].append({"pid": worker_id, "created_at": datetime.now(UTC)})
                        found = True
                        break

                if not found:
                    pointer = data[0]

                    for i in range(1, workers):
                        if len(data[i]) < len(pointer):
                            pointer = data[i]

                    pointer.append({"pid": worker_id, "created_at": datetime.now(UTC)})

                cache.set("workers", data, timeout=None)
                break

        except LockError:
            ...


app.conf.task_default_priority = 5  # Default priority value
