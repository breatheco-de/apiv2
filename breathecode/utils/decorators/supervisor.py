import asyncio
import inspect
from datetime import timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.utils import timezone

from breathecode.monitoring.models import Supervisor, SupervisorIssue

__all__ = ['supervisor', 'paths']

paths = set()


def supervisor(fn: Optional[callable] = None,
               delta: Optional[timedelta] = None,
               auto: bool = True,
               raises: bool = False):
    """Create a supervisor (automated quality assurance)."""

    def create_supervisor(fn: callable, delta: Optional[timedelta] = None, auto: bool = True, raises: bool = False):
        instance = None

        def set_instance():
            nonlocal instance

            if instance is None:
                fn_name = fn.__name__
                fn_module = fn.__module__

                from unittest.mock import call
                instance, created = Supervisor.objects.get_or_create(task_module=fn_module,
                                                                     task_name=fn_name,
                                                                     defaults={
                                                                         'delta': delta,
                                                                         'ran_at': timezone.now(),
                                                                     })

                if created is False:
                    instance.ran_at = timezone.now()
                    instance.save()

        @sync_to_async
        def aset_instance():
            set_instance()

        def wrapper(*args, **kwargs):
            nonlocal instance
            set_instance()

            res = fn(*args, **kwargs)
            if res is None:
                return

            for msg in res:
                issue, created = SupervisorIssue.objects.get_or_create(supervisor=instance,
                                                                       error=msg,
                                                                       defaults={
                                                                           'ran_at': timezone.now(),
                                                                       })

                if created is False:
                    issue.ran_at = timezone.now()
                    issue.occurrences += 1
                    issue.save()

        async def async_wrapper(*args, **kwargs):
            nonlocal instance
            await aset_instance()

            res = fn(*args, **kwargs)
            if res is None:
                return

            for msg in res:
                issue, created = await SupervisorIssue.objects.aget_or_create(supervisor=instance,
                                                                              error=msg,
                                                                              defaults={
                                                                                  'ran_at': timezone.now(),
                                                                                  'occurrences': 1
                                                                              })

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
