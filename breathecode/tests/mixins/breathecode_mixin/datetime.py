from rest_framework.test import APITestCase
from ..datetime_mixin import DatetimeMixin

__all__ = ['Datetime']


class Datetime:
    """Wrapper of last implementation of datetime mixin for testing purposes"""

    to_iso_string = DatetimeMixin.datetime_to_iso
    from_iso_string = DatetimeMixin.iso_to_datetime
    now = DatetimeMixin.datetime_now
    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent
