from datetime import datetime
from rest_framework.test import APITestCase
from ..sha256_mixin import Sha256Mixin
from ..token_mixin import TokenMixin

__all__ = ['Check']


class Check:
    """Wrapper of last implementation for request for testing purposes"""

    sha256 = Sha256Mixin.assertHash
    token = TokenMixin.assertToken
    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent

    def datetime_in_range(self, start: datetime, end: datetime, date: datetime) -> None:
        """Check if a range if between start and end argument"""

        self._parent.assertLess(start, date)
        self._parent.assertGreater(end, date)
