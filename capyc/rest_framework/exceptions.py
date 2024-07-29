import os
from typing import Optional

from django.db.models import QuerySet
from rest_framework.exceptions import APIException

from capyc.core.shorteners import C

__all__ = ["ValidationException", "PaymentException"]


def is_test_env():
    return "ENV" in os.environ and os.environ["ENV"] == "test"


class ValidationException(APIException):
    """Django REST Framework and Django Forms Exception."""

    status_code: int
    detail: str | list[C]
    queryset: Optional[QuerySet]
    data: dict
    silent: bool

    def __init__(
        self, details: str, code: int = 400, slug: Optional[str] = None, data=None, queryset=None, silent=False
    ):
        self.status_code = code
        self.detail = details
        self.data = data
        self.queryset = queryset
        self.silent = silent
        self.slug = slug or "undefined"

        if isinstance(details, list) and code == 207:
            self.detail = self._get_207_details()

        elif isinstance(details, list):
            self.detail = self._get_details()

        elif slug and is_test_env():
            self.detail = slug

    def _get_207_details(self):
        return [ValidationException(x.args[0], **x.kwargs) for x in self.detail]

    def _get_details(self):
        return [ValidationException(x.args[0], **{**x.kwargs, "code": self.status_code}) for x in self.detail]

    def get_message(self):
        if isinstance(self.detail, str):
            return self.detail

        message = ". ".join([x.detail for x in self.detail])

        if message[-1] != ".":
            message += "." if self.detail else ""

        return message

    def get_message_list(self):
        if isinstance(self.detail, list):
            message = ". ".join([x.detail for x in self.detail])

            if message[-1] != ".":
                message += "." if self.detail else ""

            return message

        return [self.detail]


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
        self.slug = slug or "undefined"

        if isinstance(details, list):
            self.detail = self._get_details()

        elif slug and is_test_env():
            self.detail = slug

    def _get_details(self):
        return [PaymentException(x.args[0], **x.kwargs) for x in self.detail]

    def get_message(self):
        if isinstance(self.detail, str):
            return self.detail

        return ". \n".join([x.kwargs["slug"] if "slug" in x.kwargs else x.args[0] for x in self.detail])

    def get_message_list(self):
        if isinstance(self.detail, list):
            return [x.kwargs["slug"] if "slug" in x.kwargs else x.args[0] for x in self.detail]

        return [self.detail]
