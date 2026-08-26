import functools
import logging
import os
from datetime import timedelta
from enum import Enum

from django.core.cache import cache
from task_manager.core.exceptions import RetryTask
from task_manager.core.settings import set_settings

from breathecode.utils.redis import Lock

__all__ = ["TaskPriority", "slots_per_dyno", "acquire_dyno_slot", "release_dyno_slot", "limit_per_dyno"]

logger = logging.getLogger(__name__)
RETRIES_LIMIT = 10
RETRY_AFTER = timedelta(seconds=5)

IS_DJANGO_REDIS = hasattr(cache, "fake") is False


# keeps this sorted by priority
# unused: ACTIVITY, TWO_FACTOR_AUTH
class TaskPriority(Enum):
    BACKGROUND = 0  # anything without importance
    NOTIFICATION = 1  # non realtime notifications
    MONITORING = 2  # monitoring tasks
    ACTIVITY = 2  # user activity
    CONTENT = 2  # related to the registry
    BILL = 2  # postpaid billing
    ASSESSMENT = 2  # user assessment
    CACHE = 3  # cache
    MARKETING = 4  # marketing purposes
    OAUTH_CREDENTIALS = 5  # oauth tasks
    DEFAULT = 5  # default priority
    TASK_MANAGER = 6  # task manager
    ACADEMY = 7  # anything that the academy can see
    CERTIFICATE = 8  # issuance of certificates
    STUDENT = 9  # anything that the student can see
    TWO_FACTOR_AUTH = 9  # 2fa
    REALTIME = 9  # schedule as soon as possible
    WEB_SERVICE_PAYMENT = 10  # payment in the web
    FIXER = 10  # fixes
    SCHEDULER = 5  # fixes


settings = {
    "RETRIES_LIMIT": 10,
    "RETRY_AFTER": timedelta(seconds=5),
    "DEFAULT": TaskPriority.DEFAULT.value,
    "SCHEDULER": TaskPriority.SCHEDULER.value,
    "TASK_MANAGER": TaskPriority.TASK_MANAGER.value,
}

set_settings(**settings)


def slots_per_dyno(per_dyno: int) -> int:
    """Concurrent slots for a task on this dyno, never above CELERY_MAX_WORKERS."""
    requested = max(1, int(per_dyno))
    max_workers = max(1, int(os.getenv("CELERY_MAX_WORKERS") or 2))
    if requested > max_workers:
        logger.warning(
            "limit_per_dyno capped requested=%s celery_max_workers=%s",
            requested,
            max_workers,
        )
        return max_workers
    return requested


def acquire_dyno_slot(
    task_name: str,
    per_dyno: int,
    *,
    timeout: int = 600,
):
    """
    Reserve one concurrent slot for `task_name` on this dyno.

    Raises RetryTask when all slots are taken so Celery retries later.
    """
    from django_redis import get_redis_connection
    from redis.exceptions import LockError

    dyno = os.getenv("DYNO") or "local"
    per_dyno = slots_per_dyno(per_dyno)

    client = get_redis_connection("default") if IS_DJANGO_REDIS else None

    for slot in range(per_dyno):
        lock = Lock(
            client,
            f"lock:task:dyno-slot:{task_name}:{dyno}:{slot}",
            timeout=timeout,
            blocking_timeout=0,
        )
        try:
            lock.__enter__()
            logger.info(
                "dyno slot acquired task=%s dyno=%s slot=%s per_dyno=%s",
                task_name,
                dyno,
                slot,
                per_dyno,
            )
            return lock
        except LockError:
            continue

    logger.warning("dyno slots exhausted task=%s dyno=%s per_dyno=%s", task_name, dyno, per_dyno)
    raise RetryTask(f"Too many {task_name} running on this dyno")


def release_dyno_slot(lock) -> None:
    if lock is None:
        return
    lock.__exit__(None, None, None)


def limit_per_dyno(per_dyno: int, *, timeout: int = 600, name: str | None = None):
    """
    Cap concurrent runs of this task on one dyno. `per_dyno` is capped by CELERY_MAX_WORKERS.

        @task(bind=True, priority=TaskPriority.ACTIVITY.value)
        @limit_per_dyno(2)
        def upload_activities(self, ...):
            ...
    """

    def decorator(func):
        task_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            slot = acquire_dyno_slot(task_name, per_dyno, timeout=timeout)
            try:
                return func(*args, **kwargs)
            finally:
                release_dyno_slot(slot)

        return wrapper

    return decorator
