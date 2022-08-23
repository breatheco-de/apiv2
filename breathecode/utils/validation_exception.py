import os
import logging
from typing import Optional
from rest_framework.exceptions import APIException
from django.db.models import QuerySet

__all__ = ['ValidationException', 'APIException']

IS_TEST_ENV = os.getenv('ENV') == 'test'
logger = logging.getLogger(__name__)


class ValidationException(APIException):
    status_code: int = 400
    default_detail: str = 'There is an error in your request'
    default_code: str = 'client_error'
    slug: Optional[str] = None

    def __init__(self, details: str, code: int = 400, slug: Optional[str] = None):
        self.status_code = code
        self.default_detail = details
        self.slug = slug
        self.detail = details

        if IS_TEST_ENV and slug:
            logger.error(f'Status {str(self.status_code)} - {slug}')
            super().__init__(slug)
        else:
            logger.error(f'Status {str(self.status_code)} - {details}')
            super().__init__(details)
