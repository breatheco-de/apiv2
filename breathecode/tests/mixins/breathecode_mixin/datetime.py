from __future__ import annotations
from datetime import timedelta
from rest_framework.test import APITestCase
from . import interfaces

from ..datetime_mixin import DatetimeMixin

__all__ = ['Datetime']


class Datetime:
    """Mixin with the purpose of cover all the related with datetime"""

    to_iso_string = DatetimeMixin.datetime_to_iso
    from_iso_string = DatetimeMixin.iso_to_datetime
    now = DatetimeMixin.datetime_now
    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc

    def from_timedelta(self, delta=timedelta(seconds=0)) -> str:
        """
        Transform from timedelta to the totals seconds in str.

        Usage:

        ```py
        from datetime import timedelta
        delta = timedelta(seconds=777)
        self.bc.datetime.from_timedelta(delta)  # equals to '777.0'
        ```
        """
        return str(delta.total_seconds())
