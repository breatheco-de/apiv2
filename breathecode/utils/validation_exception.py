import logging
import os
from typing import Optional
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException
from .shorteners import C

__all__ = ['ValidationException', 'APIException']

logger = logging.getLogger(__name__)


def is_test_env():
    return os.getenv('ENV') == 'test' or True


class ValidationException(APIException):
    status_code: int
    detail: str | list[C]
    queryset: Optional[QuerySet]
    data: dict
    silent: bool

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

        if isinstance(self.detail, str):
            logger.error(f'Status {str(self.status_code)} - {self.detail}')

    def _get_207_details(self):
        return [ValidationException(x.args[0], **x.kwargs) for x in self.detail]

    def _get_details(self):
        return [ValidationException(x.args[0], **{**x.kwargs, 'code': self.status_code}) for x in self.detail]
