"""
Tasks tests
"""
from unittest.mock import patch, call
from ...actions import get_loc_from_string
from ..mixins import JobsTestCase


class ActionGetLocFromStringTestCase(JobsTestCase):
    def test_get_locations_invalid_or_Empty_return_remote(self):
        result = get_loc_from_string('')
        result_1 = get_loc_from_string('.')
        result_2 = get_loc_from_string(')')
        result_3 = get_loc_from_string('(')

        self.assertEquals(result, ['Remote'])
        self.assertEquals(result_1, ['Remote'])
        self.assertEquals(result_2, ['Remote'])
        self.assertEquals(result_3, ['Remote'])

    def test_get_locations_valid(self):
        result = get_loc_from_string('Santiago')

        self.assertEquals(result, ['Santiago'])
