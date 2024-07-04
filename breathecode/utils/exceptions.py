__all__ = ["ProgrammingError", "MalformedLanguageCode"]

from capyc.rest_framework.exceptions import ValidationException


class ProgrammingError(Exception):
    pass


class TestError(Exception):
    pass


class MalformedLanguageCode(ValidationException):
    pass
