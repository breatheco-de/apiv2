from breathecode.utils.exceptions import ProgramingError
from celery import shared_task
from django.db import transaction
import copy

__all__ = ['task']


class Task(object):

    def __init__(self, *args, **kwargs):

        self.is_transaction = kwargs.pop('transaction', False)
        self.fallback = kwargs.pop('fallback')

        if self.fallback and not callable(self.fallback):
            raise ProgramingError('Fallback must be a callable')

        self.parent_decorator = shared_task(*args, **kwargs)

    def __call__(self, function):
        self.function = function

        def wrapper(*args, **kwargs):
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

            return function(*args, **kwargs)

        w = copy.deepcopy(wrapper)

        w.__name__ = function.__name__
        w.__module__ = function.__module__

        self.instance = self.parent_decorator(w)
        return self.instance


def task(*dargs, **dkwargs):
    return Task(*dargs, **dkwargs)
