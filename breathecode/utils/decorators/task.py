import copy
import functools
import importlib
import inspect
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

import celery
from circuitbreaker import CircuitBreakerError
from django.db import transaction
from django.utils import timezone

from breathecode.utils.exceptions import ProgrammingError

__all__ = ['task', 'AbortTask', 'RetryTask', 'RETRIES_LIMIT', 'TaskPriority', 'Task']

logger = logging.getLogger(__name__)
RETRIES_LIMIT = 10
RETRY_AFTER = timedelta(seconds=5)

from enum import Enum


# keeps this sorted by priority
# unused: ACTIVITY, TWO_FACTOR_AUTH
class TaskPriority(Enum):
    BACKGROUND = 0  # anything without importance
    NOTIFICATION = 1  # non realtime notifications
    MONITORING = 2  # monitoring tasks
    ACTIVITY = 2  # user activity
    BILL = 2  # postpaid billing
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
    SCHEDULER = 10  # fixes


class TaskException(Exception):
    """Base class for other exceptions."""

    def __init__(self, message: str, log=True) -> None:
        self.log = log
        super().__init__(message)

    def __eq__(self, other: 'TaskException'):
        return type(self) == type(other) and str(self) == str(other) and self.log == other.log


class AbortTask(TaskException):
    """Abort task due to it doesn't meet the requirements, it will not be reattempted."""

    pass


class RetryTask(TaskException):
    """Retry task due to it doesn't meet the requirements for a synchronization issue like a not found, it will be reattempted."""

    pass


def parse_payload(payload: dict):
    if not isinstance(payload, dict):
        return payload

    for key in payload.keys():
        # TypeError("string indices must be integers, not 'str'")
        if isinstance(payload[key], datetime):
            payload[key] = payload[key].isoformat().replace('+00:00', 'Z')

        elif isinstance(payload[key], Decimal):
            payload[key] = str(payload[key])

        elif isinstance(payload[key], list) or isinstance(payload[key], tuple) or isinstance(
                payload[key], set):
            l = []
            for item in payload[key]:
                l.append(parse_payload(item))

            payload[key] = l

        elif isinstance(payload[key], dict):
            payload[key] = parse_payload(payload[key])

    return payload


class Task(object):

    def __init__(self, *args, **kwargs):
        self.is_transaction = kwargs.pop('transaction', False)
        self.fallback = kwargs.pop('fallback', None)
        self.reverse = kwargs.pop('reverse', None)
        self.bind = kwargs.get('bind', False)
        self.priority = kwargs.pop('priority', TaskPriority.DEFAULT.value)
        kwargs['priority'] = TaskPriority.SCHEDULER.value

        if self.fallback and not callable(self.fallback):
            raise ProgrammingError('Fallback must be a callable')

        if self.reverse and not callable(self.reverse):
            raise ProgrammingError('Reverse must be a callable')

        self.parent_decorator = celery.shared_task(*args, **kwargs)

    def get_fn_desc(self, function: Callable) -> tuple[str, str] | tuple[None, None]:
        if not function:
            return None, None

        module_name = inspect.getmodule(function).__name__
        function_name = function.__name__

        return module_name, function_name

    def _get_fn(self, task_module: str, task_name: str) -> Callable | None:
        module = importlib.import_module(task_module)
        return getattr(module, task_name, None)

    def reattempt_settings(self) -> dict[str, datetime]:
        """Return a dict with the settings to reattempt the task."""

        return {'eta': timezone.now() + RETRY_AFTER}

    def reattempt(self, task_module: str, task_name: str, attempts: int, args: tuple[Any], kwargs: dict[str,
                                                                                                        Any]):
        x = self._get_fn(task_module, task_name)
        x.apply_async(args=args, kwargs={**kwargs, 'attempts': attempts}, **self.reattempt_settings())

    def circuit_breaker_settings(self, e: CircuitBreakerError) -> dict[str, datetime]:
        """Return a dict with the settings to reattempt the task."""

        return {'eta': timezone.now() + e._circuit_breaker.RECOVERY_TIMEOUT}

    def manage_circuit_breaker(self, e: CircuitBreakerError, task_module: str, task_name: str, attempts: int,
                               args: tuple[Any], kwargs: dict[str, Any]):
        x = self._get_fn(task_module, task_name)
        x.apply_async(args=args, kwargs={**kwargs, 'attempts': attempts}, **self.circuit_breaker_settings(e))

    def schedule(self, task_module: str, task_name: str, args: tuple[Any], kwargs: dict[str, Any]):
        """Register a task to be executed in the future."""

        x = self._get_fn(task_module, task_name)

        if self.bind:
            args = args[1:]

        return x.apply_async(args=args, kwargs=kwargs, priority=self.priority)

    def __call__(self, function):
        from breathecode.commons.models import TaskManager

        self.function = function

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            task_module, task_name = self.get_fn_desc(function)
            reverse_module, reverse_name = self.get_fn_desc(self.reverse)
            arguments = parse_payload({
                'args': args[1:] if self.bind else args,
                'kwargs': kwargs,
            })

            page = kwargs.get('page', 0)
            total_pages = kwargs.get('total_pages', 1)
            attempts = kwargs.get('attempts', None)
            task_manager_id = kwargs.get('task_manager_id', None)
            last_run = timezone.now()

            x = None
            if task_manager_id:
                x = TaskManager.objects.filter(id=task_manager_id).first()

            created = False
            if x is None:
                created = True
                x = TaskManager.objects.create(task_module=task_module,
                                               task_name=task_name,
                                               attempts=1,
                                               reverse_module=reverse_module,
                                               reverse_name=reverse_name,
                                               arguments=arguments,
                                               status='SCHEDULED',
                                               current_page=page,
                                               total_pages=total_pages,
                                               last_run=last_run)

                kwargs['task_manager_id'] = x.id

            if not created and x.status == 'SCHEDULED':
                x.status = 'PENDING'

            if not created:
                x.current_page = page + 1
                x.last_run = last_run

                if attempts:
                    x.attempts = attempts + 1

                x.save()

            if x.status in ['CANCELLED', 'REVERSED', 'PAUSED', 'ABORTED', 'DONE']:
                x.killed = True
                x.save()
                return

            if self.bind:
                t = args[0]
                t.task_manager = x

            if self.is_transaction == True:
                error = None
                with transaction.atomic():
                    sid = transaction.savepoint()
                    try:
                        if x.status == 'SCHEDULED':
                            result = self.schedule(task_module, task_name, args, kwargs)
                            x.task_id = result.id
                            x.save()
                            return

                        else:
                            x.status_message = ''
                            x.save()

                            res = function(*args, **kwargs)

                    except CircuitBreakerError as e:
                        x.status_message = str(e)[:255]

                        #TODO: think in this implementation
                        if x.attempts >= RETRIES_LIMIT:
                            logger.exception(str(e))
                            x.status = 'ERROR'
                            x.exception_module = e.__class__.__module__
                            x.exception_name = e.__class__.__name__

                            x.save()

                        else:
                            logger.warning(str(e))
                            x.save()

                            self.manage_circuit_breaker(e, x.task_module, x.task_name, x.attempts,
                                                        arguments['args'], arguments['kwargs'])

                        # it don't raise anything to manage the reattempts with the task manager
                        return

                    except RetryTask as e:
                        x.status_message = str(e)[:255]

                        if x.attempts >= RETRIES_LIMIT:
                            if e.log:
                                logger.exception(str(e))

                            x.status = 'ERROR'
                            x.exception_module = e.__class__.__module__
                            x.exception_name = e.__class__.__name__

                            x.save()

                        else:
                            if e.log:
                                logger.warning(str(e))

                            x.save()

                            self.reattempt(x.task_module, x.task_name, x.attempts, arguments['args'],
                                           arguments['kwargs'])

                        # it don't raise anything to manage the reattempts with the task manager
                        return

                    except AbortTask as e:
                        x.status = 'ABORTED'
                        x.status_message = str(e)[:255]
                        x.save()

                        if e.log:
                            logger.exception(str(e))

                        # avoid reattempts
                        return

                    except Exception as e:
                        transaction.savepoint_rollback(sid)

                        error = str(e)[:255]
                        exception = e

                        logger.exception(str(e))

                if error:
                    x.status = 'ERROR'
                    x.status_message = error
                    x.exception_module = exception.__class__.__module__
                    x.exception_name = exception.__class__.__name__

                    x.save()

                    # fallback
                    if self.fallback:
                        return self.fallback(*args, **kwargs, exception=exception)

                    # behavior by default
                    return

            else:
                try:
                    if x.status == 'SCHEDULED':
                        result = self.schedule(task_module, task_name, args, kwargs)
                        x.task_id = result.id
                        x.save()
                        return

                    else:
                        x.status_message = ''
                        x.save()

                        res = function(*args, **kwargs)

                except CircuitBreakerError as e:
                    x.status_message = str(e)[:255]

                    #TODO: things in this implementation
                    if x.attempts >= RETRIES_LIMIT:
                        logger.exception(str(e))
                        x.status = 'ERROR'
                        x.exception_module = e.__class__.__module__
                        x.exception_name = e.__class__.__name__

                        x.save()

                    else:
                        logger.warning(str(e))
                        x.save()

                        self.manage_circuit_breaker(e, x.task_module, x.task_name, x.attempts,
                                                    arguments['args'], arguments['kwargs'])

                    # it don't raise anything to manage the reattempt with the task manager
                    return

                except RetryTask as e:
                    x.status_message = str(e)[:255]

                    if x.attempts >= RETRIES_LIMIT:
                        if e.log:
                            logger.exception(str(e))

                        x.status = 'ERROR'
                        x.exception_module = e.__class__.__module__
                        x.exception_name = e.__class__.__name__

                        x.save()

                    else:
                        if e.log:
                            logger.warning(str(e))

                        x.save()

                        self.reattempt(x.task_module, x.task_name, x.attempts, arguments['args'],
                                       arguments['kwargs'])

                    # it don't raise anything to manage the reattempts with the task manager
                    return

                except AbortTask as e:
                    x.status = 'ABORTED'
                    x.status_message = str(e)[:255]
                    x.save()

                    if e.log:
                        logger.exception(str(e))

                    # avoid reattempts
                    return

                except Exception as e:
                    x.status = 'ERROR'
                    x.status_message = str(e)[:255]
                    x.exception_module = e.__class__.__module__
                    x.exception_name = e.__class__.__name__

                    x.save()

                    logger.exception(str(e))

                    # fallback
                    if self.fallback:
                        return self.fallback(*args, **kwargs, exception=e)

                    return

            if x.total_pages == x.current_page:
                x.status = 'DONE'
                x.save()

            return res

        self.instance = self.parent_decorator(wrapper)
        return self.instance


def task(*args, **kwargs):
    r"""Task wrapper that allows to use transactions, fallback and reverse functions.

    `Examples`
    ```py
    def my_reverse(*args, **kwargs):
        \"\"\"This is executed when someone reverse this task.\"\"\"

        pass


    def my_fallback(*args, **kwargs):
        \"\"\"This is executed when the task fails.\"\"\"

        pass


    @task(transaction=True, fallback=my_fallback, reverse=my_reverse)
    def my_task(*args, **kwargs):
        \"\"\"Your task, if it fails, transaction=True will made a rollback
        in the database, then fallback will be executed, if the task is
        canceled, cancel will be executed.
        \"\"\"

        pass
    """

    return Task(*args, **kwargs)
