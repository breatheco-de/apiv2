__all__ = ['ProgramingError', 'MalformedLanguageCode']

from breathecode.utils.validation_exception import ValidationException


class ProgramingError(Exception):
    pass


class TestError(Exception):
    pass


class MalformedLanguageCode(ValidationException):
    pass
