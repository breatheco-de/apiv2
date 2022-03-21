from rest_framework.test import APITestCase
from ..datetime_mixin import DatetimeMixin

__all__ = ['Datetime']


class Datetime:
    """Mixin with the purpose of cover all the related with datetime"""

    to_iso_string = DatetimeMixin.datetime_to_iso
    from_iso_string = DatetimeMixin.iso_to_datetime
    now = DatetimeMixin.datetime_now
    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent
