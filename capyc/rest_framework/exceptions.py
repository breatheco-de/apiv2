import os
from typing import Optional

# from django import forms
from django.db.models import QuerySet

# from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

# from rest_framework.exceptions import APIException, ErrorDetail, _get_codes, _get_error_details, _get_full_details
from rest_framework.exceptions import APIException

from capyc.core.shorteners import C

# from rest_framework import status

# from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

__all__ = ['ValidationException', 'PaymentException']


def is_test_env():
    return 'ENV' in os.environ and os.environ['ENV'] == 'test'


# from rest_framework.exceptions import _get_error_details

# def _get_error_details(data, default_code=None):
#     """
#     Descend into a nested data structure, forcing any
#     lazy translation strings or strings into `ErrorDetail`.
#     """
#     if isinstance(data, (list, tuple)):
#         ret = [_get_error_details(item, default_code) for item in data]
#         if isinstance(data, ReturnList):
#             return ReturnList(ret, serializer=data.serializer)
#         return ret
#     elif isinstance(data, dict):
#         ret = {key: _get_error_details(value, default_code) for key, value in data.items()}
#         if isinstance(data, ReturnDict):
#             return ReturnDict(ret, serializer=data.serializer)
#         return ret

#     text = force_str(data)
#     code = getattr(data, 'code', default_code)
#     return ErrorDetail(text, code)

# from rest_framework.exceptions import APIException
# class APIException(forms.ValidationError, APIException):
#     """
#     Base class for REST framework exceptions.
#     Subclasses should provide `.status_code` and `.default_detail` properties.
#     """
#     status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     default_detail = _('A server error occurred.')
#     default_code = 'error'

#     def __init__(self, detail=None, code=None, params=None):
#         super().__init__(self.detail, code, params)
#         if detail is None:
#             detail = self.default_detail
#         if code is None:
#             code = self.default_code

#         self.detail = _get_error_details(detail, code)

#     def __str__(self):
#         return str(self.detail)

#     def get_codes(self):
#         """
#         Return only the code part of the error details.

#         Eg. {"name": ["required"]}
#         """
#         return _get_codes(self.detail)

#     def get_full_details(self):
#         """
#         Return both the message & code parts of the error details.

#         Eg. {"name": [{"message": "This field is required.", "code": "required"}]}
#         """
#         return _get_full_details(self.detail)


# class ValidationException(APIException):
class ValidationException(APIException):
    """Django REST Framework and Django Forms Exception."""

    status_code: int
    detail: str | list[C]
    queryset: Optional[QuerySet]
    data: dict
    silent: bool

    # default_detail = _('A server error occurred.')
    # default_code = 'error'

    def __init__(self,
                 details: str,
                 code: int = 400,
                 slug: Optional[str] = None,
                 data=None,
                 queryset=None,
                 silent=False):
        self.status_code = code
        self.detail = details
        self.data = data
        self.queryset = queryset
        self.silent = silent
        self.slug = slug or 'undefined'

        if isinstance(details, list) and code == 207:
            self.detail = self._get_207_details()

        elif isinstance(details, list):
            self.detail = self._get_details()

        elif slug and is_test_env():
            self.detail = slug

    def _get_207_details(self):
        return [ValidationException(x.args[0], **x.kwargs) for x in self.detail]

    def _get_details(self):
        return [ValidationException(x.args[0], **{**x.kwargs, 'code': self.status_code}) for x in self.detail]

    def get_message(self):
        if isinstance(self.detail, str):
            return self.detail

        message = '. '.join([x.detail for x in self.detail])

        if message[-1] != '.':
            message += ('.' if self.detail else '')

        return message

    def get_message_list(self):
        if isinstance(self.detail, list):
            message = '. '.join([x.detail for x in self.detail])

            if message[-1] != '.':
                message += ('.' if self.detail else '')

            return message

        return [self.detail]

    # def __str__(self):
    #     return str(self.detail)

    # def get_codes(self):
    #     """
    #     Return only the code part of the error details.

    #     Eg. {"name": ["required"]}
    #     """
    #     return _get_codes(self.detail)

    # def get_full_details(self):
    #     """
    #     Return both the message & code parts of the error details.

    #     Eg. {"name": [{"message": "This field is required.", "code": "required"}]}
    #     """
    #     return _get_full_details(self.detail)


class PaymentException(APIException):
    status_code: int = 402
    detail: str | list[C]
    queryset: Optional[QuerySet]
    data: dict
    silent: bool

    def __init__(self, details: str, slug: Optional[str] = None, data=None, queryset=None, silent=False):
        self.detail = details
        self.data = data
        self.queryset = queryset
        self.silent = silent
        self.slug = slug or 'undefined'

        if isinstance(details, list):
            self.detail = self._get_details()

        elif slug and is_test_env():
            self.detail = slug

    def _get_details(self):
        return [PaymentException(x.args[0], **x.kwargs) for x in self.detail]

    def get_message(self):
        if isinstance(self.detail, str):
            return self.detail

        return '. \n'.join([x.kwargs['slug'] if 'slug' in x.kwargs else x.args[0] for x in self.detail])

    def get_message_list(self):
        if isinstance(self.detail, list):
            return [x.kwargs['slug'] if 'slug' in x.kwargs else x.args[0] for x in self.detail]

        return [self.detail]
