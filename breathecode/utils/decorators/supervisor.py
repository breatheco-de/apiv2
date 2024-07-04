import asyncio
import functools
import inspect
from datetime import timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.utils import timezone

from breathecode.monitoring.models import Supervisor, SupervisorIssue

__all__ = ["supervisor", "paths"]

paths = set()


def supervisor(
    fn: Optional[callable] = None, delta: Optional[timedelta] = None, auto: bool = True, raises: bool = False
):
    """Create a supervisor (automated quality assurance)."""

    def create_supervisor(fn: callable, delta: Optional[timedelta] = None, auto: bool = True, raises: bool = False):

        def get_instance():
            fn_name = fn.__name__
            fn_module = fn.__module__

            instance, created = Supervisor.objects.get_or_create(
                task_module=fn_module,
                task_name=fn_name,
                defaults={
                    "delta": delta,
                    "ran_at": timezone.now(),
                },
            )

            if created is False:
                instance.ran_at = timezone.now()
                instance.save()

            return instance

        @sync_to_async
        def aget_instance():
            return get_instance()

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            instance = get_instance()

            res = fn(*args, **kwargs)
            if res is None:
                return

            for msg in res:
                code = None
                params = None
                if isinstance(msg, tuple):
                    if len(msg) == 2:
                        msg, code = msg

                    elif len(msg) >= 3:
                        msg, code, params = msg

                issue, created = SupervisorIssue.objects.get_or_create(
                    supervisor=instance,
                    error=msg,
                    code=code,
                    params=params,
                    defaults={
                        "ran_at": timezone.now(),
                    },
                )

                if created is False:
                    issue.ran_at = timezone.now()
                    issue.occurrences += 1
                    issue.save()

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            instance = await aget_instance()

            res = await fn(*args, **kwargs)
            if res is None:
                return

            for msg in res:
                code = None
                params = None
                if isinstance(msg, tuple):
                    if len(msg) == 2:
                        msg, code = msg

                    elif len(msg) >= 3:
                        msg, code, params = msg

                issue, created = await SupervisorIssue.objects.aget_or_create(
                    supervisor=instance,
                    error=msg,
                    code=code,
                    params=params,
                    defaults={
                        "ran_at": timezone.now(),
                    },
                )

                if created is False:
                    issue.ran_at = timezone.now()
                    issue.occurrences += 1
                    await issue.asave()

        if delta is None:
            delta = timedelta(hours=1)

        paths.add((fn.__module__, fn.__name__, delta))

        if asyncio.iscoroutinefunction(fn) and inspect.isasyncgenfunction(fn):
            return async_wrapper

        return wrapper

    if fn:
        return create_supervisor(fn, delta, auto, raises)

    return create_supervisor
