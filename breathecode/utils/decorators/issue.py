import asyncio
import inspect
from datetime import timedelta
from typing import Optional

from django.db.models import Q

from breathecode.monitoring.models import SupervisorIssue

__all__ = ["issue", "paths"]

paths = {}


def issue(supervisor: callable, delta: Optional[timedelta] = None, attempts: int = 3):
    """Add a handler that is triggered by a supervisor issue."""

    if delta is None:
        delta = timedelta(minutes=10)

    def create_handler(fn: callable):
        code = fn.__name__.replace("_", "-")
        issue_by_supervisor = Q(
            code=code, supervisor__task_module=supervisor.__module__, supervisor__task_name=supervisor.__name__
        )

        def wrapper(supervisor_issue_id: int):
            issue = SupervisorIssue.objects.filter(issue_by_supervisor, fixed=None, id=supervisor_issue_id).first()
            if not issue:
                return

            params = issue.params or {}

            fixed = fn(**params)

            issue.fixed = fixed
            issue.save()

            return fixed

        async def async_wrapper(supervisor_issue_id: int):
            issue = await SupervisorIssue.objects.filter(
                issue_by_supervisor, fixed=None, id=supervisor_issue_id
            ).afirst()
            if not issue:
                return

            params = issue.params or {}

            fixed = await fn(**params)

            issue.fixed = fixed
            await issue.asave()

            return fixed

        # handler
        fn_module = fn.__module__
        fn_name = fn.__name__
        fn_path = fn_module + "." + fn_name

        # supervisor
        supervisor_module = supervisor.__module__
        supervisor_name = supervisor.__name__
        supervisor_path = supervisor_module + "." + supervisor_name

        if supervisor_path not in paths:
            paths[supervisor_path] = {}

        if code not in paths[supervisor_path]:
            paths[supervisor_path][code] = set()

        if fn_path not in paths[supervisor_path][code]:
            paths[supervisor_path][code] = (fn_module, fn_name)

        if asyncio.iscoroutinefunction(fn) and inspect.isasyncgenfunction(fn):
            async_wrapper.delta = delta
            async_wrapper.attempts = attempts
            return async_wrapper

        wrapper.delta = delta
        wrapper.attempts = attempts
        return wrapper

    return create_handler
