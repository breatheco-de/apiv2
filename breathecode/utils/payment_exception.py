import logging
import os
from typing import Optional
from django.db.models import QuerySet

from rest_framework.exceptions import APIException
from .shorteners import C

__all__ = ['PaymentException']

logger = logging.getLogger(__name__)


def is_test_env():
    return os.getenv('ENV') == 'test'


# New version
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

        if isinstance(self.detail, str):
            logger.error(f'Status {str(self.status_code)} - {self.detail}')

    def _get_details(self):
        return [ValidationException(x.args[0], **{**x.kwargs, 'code': self.status_code}) for x in self.detail]
