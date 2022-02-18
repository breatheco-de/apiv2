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

    def imperfect_equality(self, first: dict | list[dict], second: dict | list[dict]) -> None:
        """Fail if the two objects are imperfectly unequal as determined by the '==' operator"""

        assert type(first) == type(second)

        if isinstance(first, list):
            assert len(first) == len(second)

            original = []

            for i in range(0, len(first)):
                original.append(self._fill_imperfect_equality(first[i], second[i]))

        else:
            original = self._fill_imperfect_equality(first, second)

        self._parent.assertEqual(original, second)

    def _fill_imperfect_equality(self, first: dict, second: dict) -> dict:
        original = {}

        for key in second.keys():
            original[key] = second[key]

        return original
