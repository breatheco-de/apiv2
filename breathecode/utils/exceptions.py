__all__ = ['ProgrammingError', 'MalformedLanguageCode']

from breathecode.utils.validation_exception import ValidationException


class ProgrammingError(Exception):
    pass


class TestError(Exception):
    pass


class MalformedLanguageCode(ValidationException):
    pass
