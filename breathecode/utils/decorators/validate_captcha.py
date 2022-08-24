from breathecode.services.google_cloud import Recaptcha
from breathecode.utils.exceptions import ProgramingError
from ..validation_exception import ValidationException

__all__ = ['validate_captcha']


def validate_captcha(request):

    def decorator(function):

        def wrapper(*args, **kwargs):

            try:
                print(args)

            except IndexError:
                raise ProgramingError('Missing request information, use this decorator with DRF View')

            return function(*args, **kwargs)

        return wrapper

    return decorator
