import os
import logging
from typing import Optional
from rest_framework.exceptions import APIException
from django.db.models import QuerySet

__all__ = ['MultiStatusResponse']

IS_TEST_ENV = os.getenv('ENV') == 'test'
logger = logging.getLogger(__name__)


class MultiStatusResponse:
    status_code: int = 200
    detail: Optional[str] = None
    queryset: Optional[QuerySet] = None

    def __init__(self,
                 details: Optional[str] = None,
                 code: int = 200,
                 slug: Optional[str] = None,
                 queryset: Optional[QuerySet] = None):

        self.status_code = code
        self.detail = slug if IS_TEST_ENV and slug else details
        self.queryset = queryset

        if code >= 400:
            logger.error(f'Status {str(self.status_code)} - {self.detail}')

    def _get_response_info(self):
        return {'status_code': self.status_code, 'detail': self.detail, 'queryset': self.queryset}
