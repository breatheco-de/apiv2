"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_loc_from_string
from ..mixins import JobsTestCase


class ActionGetLocFromStringTestCase(JobsTestCase):
    def test_get_loc_from_string_is_Empty(self):
        result = get_loc_from_string('')
        result_1 = get_loc_from_string('.')
        result_2 = get_loc_from_string(')')
        result_3 = get_loc_from_string('(')

        self.assertEquals(result, ['Remote'])
        self.assertEquals(result_1, ['Remote'])
        self.assertEquals(result_2, ['Remote'])
        self.assertEquals(result_3, ['Remote'])
