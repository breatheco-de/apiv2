from __future__ import annotations
from datetime import datetime, timedelta
from rest_framework.test import APITestCase

from breathecode.utils.datetime_integer import DatetimeInteger
from . import interfaces

from ..datetime_mixin import DatetimeMixin

__all__ = ["Datetime"]


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

    def to_datetime_integer(self, timezone: str, date: datetime) -> int:
        """
        Transform datetime to datetime integer.

        Usage:

        ```py
        utc_now = timezone.now()

        # date
        date = datetime.datetime(2022, 3, 21, 2, 51, 55, 068)

        # equals to 202203210751
        self.bc.datetime.to_datetime_integer('america/new_york', date)
        ```
        """

        return DatetimeInteger.from_datetime(timezone, date)
