import inspect
from typing import Callable
from breathecode.utils.exceptions import ProgrammingError
from celery import shared_task
from django.db import transaction
from django.utils import timezone
import copy

__all__ = ['task']


class Task(object):

    def __init__(self, *args, **kwargs):
        self.is_transaction = kwargs.pop('transaction', False)
        self.fallback = kwargs.pop('fallback', None)
        self.reverse = kwargs.pop('reverse', None)
        self.bind = kwargs.get('bind', False)

        if self.fallback and not callable(self.fallback):
            raise ProgrammingError('Fallback must be a callable')

        if self.reverse and not callable(self.reverse):
            raise ProgrammingError('Reverse must be a callable')

        self.parent_decorator = shared_task(*args, **kwargs)

    def get_fn_desc(self, function: Callable) -> tuple[str, str] or tuple[None, None]:
        if not function:
            return None, None

        module_name = inspect.getmodule(function).__name__
        function_name = function.__name__

        return module_name, function_name

    def __call__(self, function):
        from breathecode.commons.models import TaskManager

        self.function = function

        def wrapper(*args, **kwargs):
            task_module, task_name = self.get_fn_desc(function)
            reverse_module, reverse_name = self.get_fn_desc(self.reverse)
            arguments = {
                'args': args[1:] if self.bind else args,
                'kwargs': kwargs,
            }

            page = kwargs.get('page', None)
            total_pages = kwargs.get('total_pages', None)
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
                                               reverse_module=reverse_module,
                                               reverse_name=reverse_name,
                                               arguments=arguments,
                                               status='PENDING',
                                               current_page=page,
                                               total_pages=total_pages,
                                               last_run=last_run)

                kwargs['task_manager_id'] = x.id

            if not created:
                x.current_page = page
                x.last_run = last_run
                x.save()

            if x.status in ['CANCELLED', 'REVERSED', 'PAUSED']:
                x.killed = True
                x.save()
                return

            if self.is_transaction == True:
                with transaction.atomic():
                    sid = transaction.savepoint()
                    try:
                        return function(*args, **kwargs)

                    except Exception as e:
                        transaction.savepoint_rollback(sid)

                        # fallback
                        if self.fallback:
                            return self.fallback(*args, **kwargs, exception=e)

                        # behavior by default
                        raise e

            res = function(*args, **kwargs)

            if x.total_pages is not None and x.current_page is not None and total_pages == x.current_page:
                x.status = 'DONE'
                x.save()

            return res

        w = copy.deepcopy(wrapper)

        w.__name__ = function.__name__
        w.__module__ = function.__module__

        self.instance = self.parent_decorator(w)
        return self.instance


def task(*args, **kwargs):
    """Task wrapper that allows to use transactions, fallback and reverse functions.

    Example:

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
