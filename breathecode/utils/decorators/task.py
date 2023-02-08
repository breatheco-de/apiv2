from breathecode.utils.exceptions import ProgramingError
from celery import shared_task
from django.db import transaction

__all__ = ['task']


def task(*dargs, **dkwargs):

    is_transaction = dkwargs.pop('transaction', False)
    fallback = dkwargs.pop('fallback')

    if not callable(fallback):
        raise ProgramingError('Fallback must be a callable')

    @shared_task(*dargs, **dkwargs)
    def decorator(self, function):

        def wrapper(*fargs, **fkwargs):
            # This must be a boolean

            # @shared_task(*dargs, **dkwargs)
            def inner_wrapper(*fargs, **fkwargs):
                return function(*fargs, **fkwargs)

            inner_wrapper.__name__ = function.__name__

            if is_transaction == True:
                with transaction.atomic():
                    sid = transaction.savepoint()
                    try:
                        self.__call__ = inner_wrapper
                        return self
                        return inner_wrapper()
                        return shared_task(inner_wrapper)(*dargs, **dkwargs)

                    except Exception as e:
                        transaction.savepoint_rollback(sid)
                        if fallback:
                            return fallback(*fargs, **fkwargs, exception=e)

                        return

            self.__call__ = inner_wrapper
            return self

            return inner_wrapper()
            return shared_task(inner_wrapper)(*dargs, **dkwargs)

        return wrapper

    return decorator
