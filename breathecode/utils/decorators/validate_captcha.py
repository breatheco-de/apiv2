import os
from breathecode.services.google_cloud import Recaptcha
from breathecode.utils.exceptions import ProgramingError
from ..validation_exception import ValidationException

__all__ = ['validate_captcha']


def validate_captcha(function):

    def wrapper(*args, **kwargs):
        print('decorator')
        print('args')
        print(args[0])
        try:
            data = args[0].data.copy()

            project_id = os.getenv('GOOGLE_PROJECT_ID', '')
            site_key = os.getenv('GOOGLE_CAPTCHA_KEY', '')
            token = data['token'] if 'token' in data else None
            action = data['action'] if 'action' in data else None

        except IndexError:
            raise ProgramingError('Missing request information, use this decorator with DRF View')

        return function(*args, **kwargs)

    return wrapper
